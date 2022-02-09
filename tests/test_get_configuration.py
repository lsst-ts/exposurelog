from __future__ import annotations

import pathlib
import unittest

from exposurelog.shared_state import get_shared_state
from exposurelog.testutils import assert_good_response, create_test_client


class GetRootTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_root(self) -> None:
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

    async def test_multiple_repos(self) -> None:
        """Test a server that has two repositories.

        Unfortunately I only have one test repo (and it's hard enough
        maintaining that as daf_butler evolves) so I just connect to it twice.
        """
        repo_path = pathlib.Path(__file__).parent / "data" / "LSSTCam"
        async with create_test_client(
            repo_path=repo_path,
            repo_path_2=repo_path,
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
