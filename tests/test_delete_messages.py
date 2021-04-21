from __future__ import annotations

import pathlib
import unittest

import httpx

from exposurelog.testutils import (
    TEST_SITE_ID,
    MessageDictT,
    assert_good_response,
    create_test_client,
)


def assert_good_delete_response(
    response: httpx.Response, *, message_ids: list[int]
) -> list[MessageDictT]:
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
    messages = assert_good_response(response)
    for message in messages:
        assert message["id"] in message_ids
        assert not message["is_valid"]
        assert message["date_is_valid_changed"] is not None
    return messages


class DeleteMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_delete_message(self) -> None:
        """Test adding a message."""
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        async with create_test_client(repo_path=repo_path, num_messages=5) as (
            client,
            messages,
        ):

            # Delete two messages plus one that does not exist.
            message_ids = [1, 3, 999]
            del_args = dict(ids=message_ids, site_id=TEST_SITE_ID)
            response = await client.post(
                "/exposurelog/delete_message/",
                data=del_args,
            )
            deleted_messages = assert_good_delete_response(
                response, message_ids=message_ids
            )
            assert len(deleted_messages) == 2

            # Delete the same messages again.
            # This should update ``row.date_is_valid_changed``.
            response = await client.post(
                "/exposurelog/delete_message/",
                data=del_args,
            )
            deleted_messages2 = assert_good_delete_response(
                response, message_ids=message_ids
            )
            assert len(deleted_messages2) == 2
            for message, message2 in zip(deleted_messages, deleted_messages2):
                assert (
                    message2["date_is_valid_changed"]
                    > message["date_is_valid_changed"]
                )

            # Deleting a message that does not exist should return no entries.
            del_args = dict(ids=[9999], site_id=TEST_SITE_ID)
            response = await client.post(
                "/exposurelog/delete_message/",
                data=del_args,
            )
            deleted_messages = assert_good_delete_response(
                response, message_ids=message_ids
            )
            assert len(deleted_messages) == 0

            del_args = dict(ids=[1], site_id="nonexistent")
            response = await client.post(
                "/exposurelog/delete_message/",
                data=del_args,
            )
            deleted_messages = assert_good_delete_response(
                response, message_ids=message_ids
            )
            assert len(deleted_messages) == 0
