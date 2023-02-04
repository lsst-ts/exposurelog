__all__ = [
    "TEST_SITE_ID",
    "TEST_TAGS",
    "TEST_URLS",
    "ExposureDictT",
    "MessageDictT",
    "assert_good_response",
    "assert_messages_equal",
    "AssertDataDictsOrdered",
    "AssertMessagesOrdered",
    "cast_special",
    "create_test_client",
    "modify_environ",
]


import collections.abc
import contextlib
import datetime
import http
import os
import pathlib
import random
import string
import typing
import unittest.mock
import uuid

import astropy.time
import httpx
import sqlalchemy.engine
import testing.postgresql
from sqlalchemy.ext.asyncio import create_async_engine

from . import main, shared_state
from .create_message_table import create_message_table
from .message import MESSAGE_FIELDS
from .utils import current_date_and_day_obs

# Range of dates for random messages.
MIN_DATE_RANDOM_MESSAGE = "2021-01-01"
MAX_DATE_RANDOM_MESSAGE = "2022-12-31"

TEST_SITE_ID = "test"
TEST_TAGS = "green eggs and ham".split()
TEST_URLS = [
    "https://jira.lsstcorp.org/browse/DM-1",
    "https://jira.lsstcorp.org/browse/DM-3",
    "https://jira.lsstcorp.org/browse/DM-5",
    "https://jira.lsstcorp.org/browse/DM-7",
]

# Type annotation aliases
DataDictT = dict[str, typing.Any]
MessageDictT = dict[str, typing.Any]
ExposureDictT = dict[str, typing.Any]
ArgDictT = dict[str, typing.Any]


@contextlib.asynccontextmanager
async def create_test_client(
    repo_path: pathlib.Path,
    repo_path_2: None | pathlib.Path = None,
    num_messages: int = 0,
    num_edited: int = 0,
    random_seed: int = 47,
) -> collections.abc.AsyncGenerator[
    tuple[httpx.AsyncClient, list[MessageDictT]], None
]:
    """Create the test database, test server, and httpx client."""
    random.seed(random_seed)
    with testing.postgresql.Postgresql() as postgresql:
        messages = await create_test_database(
            postgres_url=postgresql.url(),
            num_messages=num_messages,
            num_edited=num_edited,
        )

        db_config = db_config_from_dsn(postgresql.dsn())
        with modify_environ(
            # TODO DM-33642: get rid of BUTLER_WRITEABLE_HACK
            # when safe to do so.
            BUTLER_WRITEABLE_HACK="true",
            BUTLER_URI_1=str(repo_path),
            BUTLER_URI_2=None if repo_path_2 is None else str(repo_path_2),
            SITE_ID=TEST_SITE_ID,
            **db_config,
        ):
            # Note: httpx.AsyncClient does not trigger startup and shutdown
            # events. We could use asgi-lifespan's LifespanManager,
            # but it does not trigger the shutdown event if there is
            # an exception, so it does not seem worth the bother.
            assert not shared_state.has_shared_state()
            await main.startup_event()
            try:
                async with httpx.AsyncClient(
                    app=main.app, base_url="http://test"
                ) as client:
                    assert shared_state.has_shared_state()
                    yield client, messages
            finally:
                await main.shutdown_event()


@contextlib.contextmanager
def modify_environ(**kwargs: typing.Any) -> collections.abc.Iterator:
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

        ...
        def test_foo(self):
            set_value = "Value for $ENV_TO_SET"
            with modify_environ(
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
        a single message dict or a list of message dicts.
    """
    assert (
        response.status_code == http.HTTPStatus.OK
    ), f"Bad response {response.status_code}: {response.text}"
    data = response.json()
    assert "errors" not in data, f"errors={data['errors']}"
    return data


def assert_messages_equal(
    message1: MessageDictT, message2: MessageDictT
) -> None:
    """Assert that two messages are identical.

    Handle the "id" field specially because it may be a uuid.UUID or a str.
    Handle the "date_added" and "date_invalidated" fields specially
    because they may be datetime.datetime or ISOT strings.
    """
    assert message1.keys() == message2.keys()
    for field in message1:
        values = [
            cast_special(value) for value in (message1[field], message2[field])
        ]
        assert (
            values[0] == values[1]
        ), f"field {field} unequal: {values[0]!r} != {values[1]!r}"


class AssertDataDictsOrdered:
    """Assert that a list of data dicts is in the specified order.

    Parameter
    ---------
    data_name
        The data type name to use in error messages.
    """

    def __init__(self, data_name: str) -> None:
        self.data_name = data_name

    def __call__(
        self,
        data_dicts: list[dict[str, typing.Any]],
        order_by: list[str],
    ) -> None:
        """Assert that a list of data dicts is ordered as specified.

        Parameters
        ----------
        data_dicts
            Messages to test
        order_by
            Field names by which the data should be ordered.
            Each name can be prefixed by "-" to mean descending order.
            Just like the service, "id" is appended unless "id" or "-id"
            is already present
        """
        full_order_by = list(order_by)
        if not ("id" in order_by or "-id" in order_by):
            full_order_by.append("id")
        data_dict1: None | dict = None
        for data_dict2 in data_dicts:
            if data_dict1 is not None:
                self.assert_two_data_dicts_ordered(
                    data_dict1=data_dict1,
                    data_dict2=data_dict2,
                    order_by=full_order_by,
                )
            data_dict1 = data_dict2

    def assert_two_data_dicts_ordered(
        self, data_dict1: DataDictT, data_dict2: DataDictT, order_by: list[str]
    ) -> None:
        """Assert that two data_dicts are ordered as specified.

        Parameters
        ----------
        data_dict1
            A data_dict.
        data_dict2
            The next data_dict.
        order_by
            Field names by which the data should be ordered.
            Each name can be prefixed by "-" to mean descending order.
        """
        for key in order_by:
            if key.startswith("-"):
                field = key[1:]
                val1 = data_dict1[field]
                val2 = data_dict2[field]
                desired_cmp_result = 1
            else:
                field = key
                desired_cmp_result = -1
            val1 = data_dict1[field]
            val2 = data_dict2[field]
            cmp_result = self.cmp_one_field(field, val1, val2)
            if cmp_result == desired_cmp_result:
                # These two data_dicts are fine
                return
            elif cmp_result != 0:
                raise AssertionError(
                    f"{self.data_name}s mis-ordered in key {key}: "
                    f"{self.data_name}1[{field!r}]={val1!r}, "
                    f"{self.data_name}2[{field!r}]={val2!r}"
                )

    def cmp_one_field(
        self, field: str, val1: typing.Any, val2: typing.Any
    ) -> int:
        """Compare values for one field.

        Return -1 if val1 < val2, 0 if val1 == val2, 1 if val1 > val2.
        """
        if val1 == val2:
            return 0
        elif val1 > val2:
            return 1
        return -1


class AssertMessagesOrdered(AssertDataDictsOrdered):
    def __init__(self) -> None:
        super().__init__(data_name="message")

    def cmp_one_field(
        self, field: str, val1: typing.Any, val2: typing.Any
    ) -> int:
        """Overload for messages from PostgreSQL.

        Return -1 if val1 < val2, 0 if val1 == val2, 1 if val1 > val2, but:

        * Exposure_flags order is based on the order the items appear
          in the enum.
        * Value None is equal to None and larger than every value.

        This mimics how PostgreSQL handles the data.
        """
        if field == "exposure_flag":
            ordered_flag_values = dict(
                none="0: none", junk="1: junk", questionable="2: questionable"
            )
            val1 = ordered_flag_values[val1]
            val2 = ordered_flag_values[val2]
        if val1 == val2:
            return 0
        elif val1 is None:
            return 1
        elif val2 is None:
            return -1
        elif val1 > val2:
            return 1
        return -1


def cast_special(value: typing.Any) -> typing.Any:
    """Cast special types to plain data types;
    return plain old data types unchanged.

    This allows comparison between values in the database
    and values returned by the web API.

    The special types are:

    * datetime.datetime: converted to an ISO string with "T" separator.
    * uuid.UUID: convert to a string.
    """
    if isinstance(value, datetime.datetime):
        return value.isoformat(sep="T")
    elif isinstance(value, uuid.UUID):
        return str(value)
    return value


def db_config_from_dsn(dsn: dict[str, str]) -> dict[str, str]:
    """Get app database configuration arguments from a database dsn.

    The intended usage is to configure the application
    from an instance of testing.postgresql.Postgresql()::

        with testing.postgresql.Postgresql() as postgresql:
            create_test_database(postgresql.url(), num_messages=0)

            db_config = db_config_from_dsn(postgresql.dsn())
            with modify_environ(
                BUTLER_URI_1=str(repo_path),
                SITE_ID=TEST_SITE_ID,
                **db_config,
            ):
                import exposurelog.app

                client = fastapi.testclient.TestClient(exposurelog.main.app)
    """
    assert dsn.keys() <= {"port", "host", "user", "database"}
    return {
        f"exposurelog_db_{key}".upper(): str(value)
        for key, value in dsn.items()
    }


def random_bool() -> bool:
    """Return a random bool."""
    return random.random() > 0.5


def random_date(precision: int = 0) -> datetime.datetime:
    """Return a random date between MIN_DATE_RANDOM_MESSAGE
    and MAX_DATE_RANDOM_MESSAGE.

    Parameters
    ----------
    precision
        The number of decimal digits of seconds.
        If 0 then the output has no decimal point after the seconds field.

    Return the same format as dates returned from the database.
    """
    min_date_unix = astropy.time.Time(MIN_DATE_RANDOM_MESSAGE).unix
    max_date_unix = astropy.time.Time(MAX_DATE_RANDOM_MESSAGE).unix
    dsec = max_date_unix - min_date_unix
    unix_time = min_date_unix + random.random() * dsec
    return astropy.time.Time(
        unix_time, format="unix", precision=precision
    ).datetime


def random_obs_id() -> str:
    """Return a random obs_id.

    The format is aa_a_YYYYMMDD_dddddd, where:

    * a is an uppercase letter,
    * YYYYMMDD is the current day_obs (current TAI - 12 hours).
    * d is a digit
    """
    current_day_obs = current_date_and_day_obs()[1]
    fields = (
        "".join(random.sample(string.ascii_uppercase, 2)),
        random.choice(string.ascii_uppercase),
        str(current_day_obs),
        "".join(random.sample(string.digits, 6)),
    )
    return "_".join(fields)


def random_str(nchar: int) -> str:
    """Return a random string of nchar printable UTF-8 characters.

    The list of characters is limited, but attempts to
    cover a wide range of potentially problematic characters
    including ' " \t \n \\ and an assortment of non-ASCII characters.
    """
    chars = list(
        "abcdefgABCDEFG012345 \t\n\r"
        "'\"“”`~!@#$%^&*()-_=+[]{}\\|,.<>/?"
        "¡™£¢∞§¶•ªº–≠“‘”’«»…ÚæÆ≤¯≥˘÷¿"
        "œŒ∑„®‰†ˇ¥ÁüîøØπ∏åÅßÍ∂ÎƒÏ©˝˙Ó∆Ô˚¬ÒΩ¸≈˛çÇ√◊∫ıñµÂ"
        "✅😀⭐️🌈🌎1️⃣🟢❖🍏🪐💫🥕🥑🌮🥗🚠🚞🚀⚓️🚁🚄🏝🧭🕰📡🗝📅🖋🔎❤️☮️"
    )
    return "".join(random.sample(chars, nchar))


def random_words(words: list[str], max_num: int = 3) -> list[str]:
    """Return a list of 0 or more allowed words.

    Parameters
    ----------
    words
        List of words from which to select words.
    max_num
        The maximum number of returned words.

    Half of the time it will return 0 items.
    The rest of the time it will return 1 - max_num values
    in random order, with equal probability per number of returned words.
    """
    if random.random() < 0.5:
        return []
    num_words = random.randint(1, max_num)
    return random.sample(words, num_words)


def random_message() -> MessageDictT:
    """Make one random message, as a dict of field: value.

    All messages will have ``id=None``, ``site_id=TEST_SITE_ID``,
    ``is_valid=True``, ``date_invalidated=None``, and ``parent_id=None``.

    Fields are in the same order as `Message`, to make it easier
    to visually compare these messages to messages in responses.

    String are random unicode characters, and each string field has
    a slightly different arbitrary length.
    Tags and urls are generated from a random selection (of random length)
    of possible tags and URLs.

    To use:

    * Call multiple times to make a list of messages.
    * Sort that list by ``date_added``.
    * Add the ``id`` field, in order, starting at 1.
    * Optionally modify some messages to be edited versions
      of earlier messages, as follows:

      * Set edited_message["parent_id"] = parent_message["id"]
      * Set parent_message["is_valid"] = False
      * Set parent_message["date_invalidated"] =
        edited_message["date_added"]
    """
    random_yyyymmdd = astropy.time.Time(random_date()).strftime("%Y%m%d")

    message = dict(
        id=None,
        site_id=TEST_SITE_ID,
        obs_id=random_obs_id(),
        instrument=random_str(nchar=16),
        day_obs=int(random_yyyymmdd),
        message_text=random_str(nchar=20),
        level=random.randint(0, 40),
        tags=random_words(TEST_TAGS),
        urls=random_words(TEST_URLS),
        user_id=random_str(nchar=14),
        user_agent=random_str(nchar=12),
        is_human=random_bool(),
        is_valid=True,
        exposure_flag=random.choice(["none", "junk", "questionable"]),
        date_added=random_date(),
        date_invalidated=None,
        parent_id=None,
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

    The list will be in order of increasing ``date_added``.

    Link about half of the messages to an older message.
    """
    message_list = [random_message() for i in range(num_messages)]
    message_list.sort(key=lambda message: message["date_added"])
    for i, message in enumerate(message_list):
        message["id"] = uuid.uuid4()

    # Create edited messages.
    parent_message_id_set: set[uuid.UUID] = set()
    edited_messages: list[MessageDictT] = list(
        # [1:] because there is no older message to be the parent.
        random.sample(message_list[1:], num_edited)
    )
    edited_messages.sort(key=lambda message: message["date_added"])
    for i, message in enumerate(edited_messages):
        while True:
            parent_message = random.choice(message_list[0 : i + 1])
            if parent_message["id"] not in parent_message_id_set:
                parent_message_id_set.add(parent_message["id"])
                break
        message["parent_id"] = parent_message["id"]
        parent_message["is_valid"] = False
        parent_message["date_invalidated"] = message["date_added"]
    return message_list


async def create_test_database(
    postgres_url: str,
    num_messages: int,
    num_edited: int = 0,
) -> list[MessageDictT]:
    """Create a test database, initialize it with random messages,
    and return the messages.

    Parameters
    ----------
    postgresql_url
        URL to PostgreSQL database. Typically a test database created using::

            with testing.postgresql.Postgresql() as postgresql:
                postgres_url = postgresql.url()
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
    sa_url = sqlalchemy.engine.make_url(postgres_url)
    sa_url = sa_url.set(drivername="postgresql+asyncpg")
    engine = create_async_engine(sa_url, future=True)

    table = create_message_table()
    async with engine.begin() as connection:
        await connection.run_sync(table.metadata.create_all)

    messages = random_messages(
        num_messages=num_messages, num_edited=num_edited
    )
    async with engine.begin() as connection:
        for message in messages:
            # Do not insert the "is_valid" field
            # because it is computed.
            pruned_message = message.copy()
            del pruned_message["is_valid"]
            result = await connection.execute(
                table.insert()
                .values(**pruned_message)
                .returning(table.c.id, table.c.is_valid)
            )
            data = result.fetchone()
            assert data is not None  # Make mypy happy.
            assert message["id"] == data.id
            assert message["is_valid"] == data.is_valid

    return messages
