from __future__ import annotations

import pathlib
import unittest

import httpx

from exposurelog.testutils import (
    ArgDictT,
    MessageDictT,
    assert_good_response,
    create_test_client,
)


def assert_good_edit_response(
    response: httpx.Response,
    *,
    old_message: MessageDictT,
    edit_args: ArgDictT,
) -> MessageDictT:
    """Assert that an edit_message command succeeded and return the new
    message.
    """
    new_message = assert_good_response(response)
    assert new_message["parent_id"] == old_message["id"]
    assert new_message["parent_site_id"] == old_message["site_id"]
    assert new_message["is_valid"]
    assert not old_message["is_valid"]
    assert new_message["date_is_valid_changed"] is None
    assert old_message["date_is_valid_changed"] is not None
    for key in old_message:
        if key in set(
            (
                "id",
                "site_id",
                "is_valid",
                "parent_id",
                "parent_site_id",
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


class EditMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_edit_message(self) -> None:
        """Test editing a message."""
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        async with create_test_client(repo_path=repo_path, num_messages=1) as (
            client,
            messages,
        ):
            old_id = messages[0]["id"]
            old_site_id = messages[0]["site_id"]

            find_old_message_args = dict(
                min_id=old_id,
                max_id=old_id + 1,
                site_ids=[old_site_id],
                is_valid=False,
            )
            full_edit_args = dict(
                id=old_id,
                site_id=old_site_id,
                message_text="New message text",
                user_id="new user_id",
                user_agent="new user_agent",
                is_human=True,
                exposure_flag="junk",
            )
            # Repeatedly edit the old message. Each time
            # add a new version of the message with one field omitted,
            # to check that the one field is not changed from the original.
            # After each edit, find the old message and check that
            # the date_is_valid_changed has been suitably updated.
            for del_key in full_edit_args:
                if del_key in ("id", "site_id"):
                    # Skip required arguments
                    continue
                edit_args = full_edit_args.copy()
                del edit_args[del_key]
                edit_response = await client.post(
                    "/exposurelog/edit_message/", data=edit_args
                )
                find_old_response = await client.get(
                    "/exposurelog/find_messages/", params=find_old_message_args
                )
                old_messages = assert_good_response(find_old_response)
                assert len(old_messages) == 1
                old_message = old_messages[0]
                assert_good_edit_response(
                    edit_response,
                    old_message=old_message,
                    edit_args=edit_args,
                )

            # Error: must specify "id".
            # This is a schema violation so the error code is 422,
            # but I have not found that documented so
            # accept anything in the 400s
            bad_edit_args = edit_args.copy()
            del bad_edit_args["id"]
            response = await client.post(
                "/exposurelog/edit_message/", data=bad_edit_args
            )
            assert 400 <= response.status_code < 500

            # Error: edit a message that does not exist.
            bad_edit_args = edit_args.copy()
            bad_edit_args["id"] = 9999
            response = await client.post(
                "/exposurelog/edit_message/", data=bad_edit_args
            )
            assert response.status_code == 404
