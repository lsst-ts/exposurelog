from __future__ import annotations

__all__ = [
    "modify_environ",
    "MessageDictT",
    "assert_good_response",
    "create_test_client",
    "create_test_database",
]

import contextlib
import os
import pathlib
import typing
import unittest.mock

import asgi_lifespan
import astropy.time
import httpx
import numpy as np
import sqlalchemy as sa
import testing.postgresql

from .create_messages_table import create_messages_table
from .message import MESSAGE_FIELDS

# Range of dates for random messages.
MIN_DATE_RANDOM_MESSAGE = "2021-01-01"
MAX_DATE_RANDOM_MESSAGE = "2022-12-31"

TEST_SITE_ID = "test"

random = np.random.RandomState(47)

# Type annotation aliases
MessageDictT = typing.Dict[str, typing.Any]
ArgDictT = typing.Dict[str, typing.Any]


@contextlib.asynccontextmanager
async def create_test_client(
    repo_path: pathlib.Path,
    num_messages: int,
    num_edited: int = 0,
) -> typing.AsyncGenerator[
    typing.Tuple[httpx.AsyncClient, typing.List[MessageDictT]], None
]:
    """Create the test database, test server, and httpx client."""
    with testing.postgresql.Postgresql() as postgresql:
        messages = create_test_database(
            postgresql, num_messages=num_messages, num_edited=num_edited
        )

        db_config = db_config_from_dsn(postgresql.dsn())
        with modify_environ(
            BUTLER_URI_1=str(repo_path),
            SITE_ID=TEST_SITE_ID,
            **db_config,
        ):
            # Wait to import shared_state until the environment is configured.
            # Note that exposurelog.app imports exposurelog.shared_state.
            import exposurelog.app
            import exposurelog.shared_state

            assert not exposurelog.shared_state.has_shared_state()
            async with asgi_lifespan.LifespanManager(exposurelog.app.app):
                async with httpx.AsyncClient(
                    app=exposurelog.app.app, base_url="http://test"
                ) as client:
                    assert exposurelog.shared_state.has_shared_state()
                    yield client, messages


@contextlib.contextmanager
def modify_environ(**kwargs: typing.Any) -> typing.Iterator:
    """Context manager to temporarily patch os.environ.

    This calls `unittest.mock.patch` and is only intended for unit tests.

    Parameters
    ----------
    kwargs : `dict` [`str`, `str` or `None`]
        Environment variables to set or clear.
        Each key is the name of an environment variable (with correct case);
        it need not already exist. Each value must be one of:

        * A string value to set the env variable.
        * None to delete the env variable, if present.

    Raises
    ------
    RuntimeError
        If any value in kwargs is not of type `str` or `None`.

    Notes
    -----
    Example of use::

        from lsst.ts import salobj
        ...
        def test_foo(self):
            set_value = "Value for $ENV_TO_SET"
            with salobj.modify_environ(
                HOME=None,  # Delete this env var
                ENV_TO_SET=set_value,  # Set this env var
            ):
                self.assertNotIn("HOME", os.environ)
                self.assert(os.environ["ENV_TO_SET"], set_value)
    """
    bad_value_strs = [
        f"{name}: {value!r}"
        for name, value in kwargs.items()
        if not isinstance(value, str) and value is not None
    ]
    if bad_value_strs:
        raise RuntimeError(
            "The following arguments are not of type str or None: "
            + ", ".join(bad_value_strs)
        )

    new_environ = os.environ.copy()
    for name, value in kwargs.items():
        if value is None:
            new_environ.pop(name, None)
        else:
            new_environ[name] = value
    with unittest.mock.patch("os.environ", new_environ):
        yield


def assert_good_response(response: httpx.Response) -> typing.Any:
    """Assert that a response is good and return the data.

    Parameters
    ----------
    command
        The command. If None then return the whole response, else return
        the response from the command (response["data"][command]) --
        a single message dict or a list of messages dicts.
    """
    assert response.status_code == 200
    data = response.json()
    assert "errors" not in data, f"errors={data['errors']}"
    return data


def db_config_from_dsn(dsn: dict[str, str]) -> dict[str, str]:
    """Get app database configuration arguments from a database dsn.

    The intended usage is to configure the application
    from an instance of testing.postgresql.Postgresql()::

        with testing.postgresql.Postgresql() as postgresql:
            create_test_database(postgresql, num_messages=0)

            with modify_environ(
                BUTLER_URI_1=str(repo_path),
                SITE_ID=TEST_SITE_ID,
                **db_config,
            ):
                import exposurelog.app

                client = fastapi.testclient.TestClient(exposurelog.app.app)
    """
    assert dsn.keys() <= {"port", "host", "user", "database"}
    return {
        f"exposurelog_db_{key}".upper(): str(value)
        for key, value in dsn.items()
    }


random = np.random.RandomState(47)


def random_bool() -> bool:
    return random.rand() > 0.5


def random_date(precision: int = 0) -> astropy.time.Time:
    min_date_unix = astropy.time.Time(MIN_DATE_RANDOM_MESSAGE).unix
    max_date_unix = astropy.time.Time(MAX_DATE_RANDOM_MESSAGE).unix
    dsec = max_date_unix - min_date_unix
    unix_time = min_date_unix + random.rand() * dsec
    return astropy.time.Time(unix_time, format="unix", precision=precision).iso


def random_str(nchar: int) -> str:
    """Return a random string of printable UTF-8 characters.

    The list of characters is limited, but attempts to
    cover a wide range of potentially problematic characters
    including ' " \t \n \\ and an assortment of non-ASCII characters.
    """
    chars = list(
        "abcdefgABCDEFG012345 \t\n\r"
        "'\"“”`~!@#$%^&*()-_=+[]{}\\|,.<>/?"
        "¡™£¢∞§¶•ªº–≠“‘”’«»…ÚæÆ≤¯≥˘÷¿"
        "œŒ∑„®‰†ˇ¥ÁüîøØπ∏åÅßÍ∂ÎƒÏ©˝˙Ó∆Ô˚¬ÒΩ¸≈˛çÇ√◊∫ıñµÂ"
    )
    return "".join(random.choice(chars, size=(20,)))


def random_message() -> MessageDictT:
    """Make one random message, as a dict of field: value.

    All messages will have ``id=None``, ``site_id=TEST_SITE_ID``,
    ``is_valid=True``, ``date_is_valid_changed=None``,
    ``parent_id=None``, and ``parent_site_id=None``.

    Fields are in the same order as `Message` and the database schema,
    to make it easier to visually compare these messages to messages in
    responses.

    String are random ASCII characters, and each string field has
    a slightly different arbitrary length.

    To use:

    * Call multiple times to make a list of messages.
    * Sort that list by ``date_added``.
    * Add the ``id`` field, in order, starting at 1.
    * Optionally modify some messages to be edited versions
      of earlier messages, as follows:

      * Set edited_message["parent_id"] = parent_message["id"]
      * Set edited_message["parent_site_id"] = parent_message["site_id"]
      * Set parent_message["is_valid"] = False
      * Set parent_message["date_is_valid_changed"] =
        edited_message["date_added"]
    """
    random_yyyymmdd = astropy.time.Time(random_date()).strftime("%Y%m%d")

    message = dict(
        id=None,
        site_id=TEST_SITE_ID,
        obs_id=random_str(nchar=18),
        instrument=random_str(nchar=16),
        day_obs=int(random_yyyymmdd),
        message_text=random_str(nchar=20),
        user_id=random_str(nchar=14),
        user_agent=random_str(nchar=12),
        is_human=random_bool(),
        is_valid=True,
        exposure_flag=random.choice(["none", "junk", "questionable"]),
        date_added=random_date(),
        date_is_valid_changed=None,
        parent_id=None,
        parent_site_id=None,
    )

    # Check that we have set all fields (not necessarily in order).
    assert set(message) == set(MESSAGE_FIELDS)

    return message


def random_messages(num_messages: int, num_edited: int) -> list[MessageDictT]:
    """Make a list of random messages, each a dict of field: value.

    Parameters
    ----------
    num_messages
        Number of messages
    num_edited
        Number of these messages that should be edited versions
        of earlier messages.

    Notes
    -----

    The list will be in order of increasing ``date_added``,
    which is also the order of increasing ``id``.
    You must delete the ``id`` field before adding the message to the
    database, for example::


    Link about half of the messages to an older message.
    """
    message_list = [random_message() for i in range(num_messages)]
    message_list.sort(key=lambda message: message["date_added"])
    for i, message in enumerate(message_list):
        message["id"] = i + 1

    # Create edited messages.
    parent_message_id_set = set()
    edited_messages = list(
        # [1:] because there is no older message to be the parent
        random.choice(message_list[1:], size=num_edited, replace=False)
    )
    edited_messages.sort(key=lambda message: message["id"])
    for message in edited_messages:
        message_id = message["id"]
        while True:
            parent_message = random.choice(message_list[0 : message_id - 1])
            if parent_message["id"] not in parent_message_id_set:
                parent_message_id_set.add(parent_message["id"])
                break
        message["parent_id"] = parent_message["id"]
        message["parent_site_id"] = parent_message["site_id"]
        parent_message["is_valid"] = False
        parent_message["date_is_valid_changed"] = message["date_added"]
    return message_list


def create_test_database(
    postgresql: testing.postgresql.Postgresql,
    num_messages: int,
    num_edited: int = 0,
) -> list[MessageDictT]:
    """Create a test database, initialize it with random messages,
    and return the messages.

    Parameters
    ----------
    postgresql
        Test database. Typically created using::

            with testing.postgresql.Postgresql() as postgresql:
    num_messages
        Number of messages
    num_edited, optional
        Number of these messages that should be edited versions
        of earlier messages. Must be 0 or < ``num_messages``.

    Returns
    -------
    messages
        The randomly created messages. Each message is a dict of field: value
        and all fields are set.
    """
    if num_edited > 0 and num_edited >= num_messages:
        raise ValueError(
            f"num_edited={num_edited} must be zero or "
            f"less than num_messages={num_messages}"
        )
    engine = sa.create_engine(postgresql.url())

    table = create_messages_table(engine=engine)
    table.metadata.create_all(engine)

    messages = random_messages(
        num_messages=num_messages, num_edited=num_edited
    )
    with engine.connect() as connection:
        for message in messages:
            message_without_id = message.copy()
            del message_without_id["id"]
            result = connection.execute(
                table.insert()
                .values(**message_without_id)
                .returning(table.c.id)
            )
            data = result.fetchone()
            assert data[0] == message["id"]

    return messages
