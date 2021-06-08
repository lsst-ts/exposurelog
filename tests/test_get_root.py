from __future__ import annotations

import http
import pathlib
import unittest

from exposurelog.testutils import create_test_client


class GetRootTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_root(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        async with create_test_client(repo_path=repo_path, num_messages=0) as (
            client,
            messages,
        ):
            response = await client.get("/exposurelog")
            assert response.status_code == http.HTTPStatus.OK
            assert "Exposure log" in response.text
            assert "/exposurelog/docs" in response.text
            assert "OpenAPI" in response.text
