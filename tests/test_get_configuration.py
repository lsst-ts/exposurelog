from __future__ import annotations

import pathlib
import unittest

from exposurelog.shared_state import get_shared_state
from exposurelog.testutils import assert_good_response, create_test_client


class GetConfigurationTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_one_butler(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "LSSTCam"
        async with create_test_client(repo_path=repo_path, num_messages=0) as (
            client,
            messages,
        ):
            shared_state = get_shared_state()
            for suffix in ("", "/"):
                response = await client.get(
                    "/exposurelog/configuration" + suffix
                )
                data = assert_good_response(response)
                assert data["site_id"] == shared_state.site_id
                assert data["butler_uri_1"] == shared_state.butler_uri_1
                assert data["butler_uri_2"] == ""

    async def test_two_butlers(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "LSSTCam"
        repo_path_2 = pathlib.Path(__file__).parent / "data" / "LATISS"
        async with create_test_client(
            repo_path=repo_path,
            repo_path_2=repo_path_2,
        ) as (
            client,
            messages,
        ):
            shared_state = get_shared_state()
            assert len(shared_state.registries) == 2
            response = await client.get("/exposurelog/configuration")
            data = assert_good_response(response)
            assert data["site_id"] == shared_state.site_id
            assert data["butler_uri_1"] == shared_state.butler_uri_1
            assert data["butler_uri_2"] == shared_state.butler_uri_2
