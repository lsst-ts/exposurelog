from __future__ import annotations

import pathlib
import unittest
import uuid

from exposurelog.testutils import (
    assert_good_response,
    assert_messages_equal,
    create_test_client,
)


class GetMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_message(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        async with create_test_client(repo_path=repo_path, num_messages=5) as (
            client,
            messages,
        ):
            id = messages[2]["id"]
            print("get message with id=", id)
            response = await client.get(f"/exposurelog/messages/{id}")
            message = assert_good_response(response)
            assert_messages_equal(message, messages[2])

            # Test that a non-existent message returns 404
            bad_id = uuid.uuid4()
            response = await client.get(f"/exposurelog/messages/{bad_id}")
            assert response.status_code == 404
