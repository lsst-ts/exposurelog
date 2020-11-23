from __future__ import annotations

import pathlib
import typing

import aiohttp
import testing.postgresql

from exposurelog.app import create_app
from exposurelog.testutils import (
    MessageDictT,
    Requestor,
    assert_good_response,
    create_test_database,
    db_config_from_dsn,
)

if typing.TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


async def assert_good_delete_response(
    response: aiohttp.ClientResponse, *, message_ids: typing.List[int]
) -> typing.List[MessageDictT]:
    """Check the response from a successful delete_messages request.

    Parameters
    ----------
    response
        Response to HTTP request.
    message_ids
        ID of message that was deleted.

    Returns
    -------
    messages
        The messages that were deleted, as a list of dict.
    """
    messages = await assert_good_response(response, command="delete_messages")
    for message in messages:
        assert message["id"] in message_ids
        assert not message["is_valid"]
        assert message["date_is_valid_changed"] is not None
    return messages


async def test_delete_message(aiohttp_client: TestClient) -> None:
    """Test adding a message."""
    num_messages = 5
    repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
    with testing.postgresql.Postgresql() as postgresql:
        create_test_database(postgresql, num_messages=num_messages)

        db_config = db_config_from_dsn(postgresql.dsn())
        app = create_app(**db_config, butler_uri_1=repo_path)
        name = app["safir/config"].name

        client = await aiohttp_client(app)
        await app["exposurelog/exposurelog_db"].start_task

        requestor = Requestor(
            client=client,
            category="mutation",
            command="delete_messages",
            url_suffix=name,
        )

        # Delete two messages plus one that does not exist.
        message_ids = [1, 3, 999]
        del_args = dict(ids=message_ids)
        response = await requestor(del_args)
        deleted_messages = await assert_good_delete_response(
            response, message_ids=message_ids
        )
        assert len(deleted_messages) == 2

        # Delete the same messages again.
        # This should update ``row.date_is_valid_changed``.
        response = await requestor(del_args)
        deleted_messages2 = await assert_good_delete_response(
            response, message_ids=message_ids
        )
        assert len(deleted_messages2) == 2
        for message, message2 in zip(deleted_messages, deleted_messages2):
            assert (
                message2["date_is_valid_changed"]
                > message["date_is_valid_changed"]
            )

        # Deleting a message that does not exist should return no entries.
        del_args = dict(ids=[9999])
        response = await requestor(del_args)
        deleted_messages = await assert_good_delete_response(
            response, message_ids=message_ids
        )
        assert len(deleted_messages) == 0
