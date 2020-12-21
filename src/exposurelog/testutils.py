from __future__ import annotations

__all__ = [
    "MessageDictT",
    "Requestor",
    "assert_bad_response",
    "assert_good_response",
    "create_test_database",
]

import typing

import astropy
import numpy as np
import sqlalchemy as sa

from exposurelog.create_messages_table import create_messages_table
from exposurelog.format_http_request import format_http_request
from exposurelog.schemas.message_type import MessageType

if typing.TYPE_CHECKING:
    import aiohttp
    import aiohttp.test_utils
    import testing.postgresql


# Range of dates for random messages.
MIN_DATE_RANDOM_MESSAGE = "2021-01-01"
MAX_DATE_RANDOM_MESSAGE = "2022-12-31"

TEST_SITE_ID = "test"

random = np.random.RandomState(47)

# Type annotation aliases
MessageDictT = typing.Dict[str, typing.Any]
ArgDictT = typing.Dict[str, typing.Any]


class Requestor:
    """Functor to issue GraphQL requests.

    Parameters
    ----------
    client
        aiohttp client.
    category
        Default request category: "mutation" or "query"
    command
        Default command.
    url_suffix
        URL suffix for requests, e.g. exposurelog
    """

    def __init__(
        self,
        client: aiohttp.test_utils.TestClient,
        category: str,
        command: str,
        url_suffix: str,
    ):
        if category not in ("mutation", "query"):
            raise ValueError(f"category={category} must be mutation or query")
        self.client = client
        self.category = category
        self.command = command
        self.url_suffix = url_suffix

    async def __call__(
        self, args_dict: dict, category: str = None, command: str = None
    ) -> aiohttp.ClientResponse:
        """Issue a request.

        Parameters
        ----------
        command
            Command to issue.
        args_dict
            Arguments for the command.

        Returns
        -------
        response
            Client response.
        """
        if category is None:
            category = self.category
        if command is None:
            command = self.command
        args_data, headers = format_http_request(
            category=category,
            command=command,
            args_dict=args_dict,
        )
        return await self.client.post(
            self.url_suffix, json=args_data, headers=headers
        )


async def assert_bad_response(response: aiohttp.ClientResponse) -> dict:
    """Check the response from an unsuccessful request.

    Parameters
    ----------
    response
        Response to HTTP request.

    Returns
    -------
    data
        The full data returned from response.json()
    """
    assert response.status == 200
    data = await response.json()
    assert "errors" in data
    return data


async def assert_good_response(
    response: aiohttp.ClientResponse, command: str = None
) -> typing.Any:
    """Assert that a response is good and return the data.

    Parameters
    ----------
    command
        The command. If None then return the whole response, else return
        the response from the command (response["data"][command]) --
        a single message dict or a list of messages dicts.
    """
    assert response.status == 200
    data = await response.json()
    assert "errors" not in data, f"errors={data['errors']}"
    if command:
        return data["data"][command]
    return data


def db_config_from_dsn(dsn: typing.Dict[str, str]) -> typing.Dict[str, str]:
    """Get app database configuration arguments from a database dsn.

    The intended usage is to configure the application
    from an instance of testing.postgresql.Postgresql()::

        with testing.postgresql.Postgresql() as postgresql:
            create_test_database(postgresql, num_messages=0)

            config_args = db_config_from_dsn(postgresql.dsn())
            app = create_app(
                **db_config_args,
                butler_uri_1=repo_path
            )
    """
    assert dsn.keys() <= {"port", "host", "user", "database"}
    return {f"exposurelog_db_{key}": value for key, value in dsn.items()}


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

    Fields are in the same order as MessageType and the database schema,
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
    assert set(message) == set(MessageType.fields)

    return message


def random_messages(
    num_messages: int, num_edited: int
) -> typing.List[MessageDictT]:
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
) -> typing.List[MessageDictT]:
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
