import pathlib
import unittest

from exposurelog.testutils import assert_good_response, create_test_client


class GetInstrumentsTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_one_butler(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "LATISS"
        async with create_test_client(repo_path=repo_path, num_messages=0) as (
            client,
            messages,
        ):
            for suffix in ("", "/"):
                response = await client.get(
                    "/exposurelog/instruments" + suffix
                )
                data = assert_good_response(response)
                assert data["butler_instruments_1"] == ["LATISS"]
                assert data["butler_instruments_2"] == []

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
            response = await client.get("/exposurelog/instruments")
            data = assert_good_response(response)
            assert data["butler_instruments_1"] == ["LSSTCam"]
            assert data["butler_instruments_2"] == ["LATISS"]
