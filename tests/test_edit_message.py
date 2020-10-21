from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import testing.postgresql

from owl.app import create_app
from owl.testutils import (
    ArgDictT,
    MessageDictT,
    Requestor,
    assert_bad_response,
    assert_good_response,
    create_test_database,
)

if TYPE_CHECKING:
    import aiohttp
    from aiohttp.pytest_plugin.test_utils import TestClient


async def assert_good_edit_response(
    response: aiohttp.ClientResponse,
    *,
    old_message: MessageDictT,
    edit_args: ArgDictT,
) -> MessageDictT:
    """Assert that an edit_message command succeeded and return the new
    message.
    """
    new_message = await assert_good_response(response, command="edit_message")
    assert new_message["parent_id"] == old_message["id"]
    assert new_message["is_valid"]
    assert not old_message["is_valid"]
    assert new_message["date_is_valid_changed"] is None
    assert old_message["date_is_valid_changed"] is not None
    for key in old_message:
        if key in set(
            (
                "id",
                "is_valid",
                "parent_id",
                "date_added",
                "is_valid",
                "date_is_valid_changed",
            )
        ):
            # These are handled above, except date_added,
            # which should not match.
            continue
        elif key in edit_args:
            assert new_message[key] == edit_args[key]
        else:
            assert new_message[key] == old_message[key]
    return new_message


async def test_edit_message(aiohttp_client: TestClient) -> None:
    """Test editing a message."""
    repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
    with testing.postgresql.Postgresql() as postgresql:
        messages = create_test_database(postgresql=postgresql, num_messages=1)

        app = create_app(
            owl_database_url=postgresql.url(), butler_uri_1=repo_path
        )
        name = app["safir/config"].name

        client = await aiohttp_client(app)
        await app["owl/owl_database"].start_task

        requestor = Requestor(
            client=client,
            category="mutation",
            command="edit_message",
            url_suffix=f"{name}/graphql",
        )

        old_message_id = messages[0]["id"]

        find_old_message_args = dict(
            min_id=old_message_id, max_id=old_message_id + 1
        )
        full_edit_args = dict(
            id=old_message_id,
            message_text="New message text",
            user_id="new user_id",
            user_agent="new user_agent",
            is_human=True,
            exposure_flag="junk",
        )
        # Repeatedly edit the old message.
        # Each time add a new version of the message with one field omitted,
        # to check that the one field is not changed from the original.
        # After each edit, find the old message and check that
        # the date_is_valid_changed has been suitably updated.
        for del_key in full_edit_args:
            if del_key == "id":
                continue  # id is required
            edit_args = full_edit_args.copy()
            del edit_args[del_key]
            edit_response = await requestor(edit_args)
            find_old_response = await requestor(
                find_old_message_args,
                category="query",
                command="find_messages",
            )
            old_messages = await assert_good_response(
                find_old_response, command="find_messages"
            )
            assert len(old_messages) == 1
            old_message = old_messages[0]
            await assert_good_edit_response(
                edit_response,
                old_message=old_message,
                edit_args=edit_args,
            )

        # Error: must specify "id".
        # This is a schema violation, so the response status is 400.
        bad_edit_args = edit_args.copy()
        del bad_edit_args["id"]
        response = await requestor(bad_edit_args)
        assert response.status == 400

        # Error: edit a message that does not exist.
        bad_edit_args = edit_args.copy()
        bad_edit_args["id"] = 9999
        response = await requestor(bad_edit_args)
        await assert_bad_response(response)
