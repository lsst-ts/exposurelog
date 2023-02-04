import http
import pathlib
import random
import unittest

import astropy.time
import httpx

from exposurelog.testutils import (
    TEST_TAGS,
    TEST_URLS,
    MessageDictT,
    assert_good_response,
    create_test_client,
    random_obs_id,
)
from exposurelog.utils import current_date_and_day_obs


def assert_good_add_response(
    response: httpx.Response, add_args: dict
) -> MessageDictT:
    """Check the response from a successful add_messages request.

    Parameters
    ----------
    response
        Response to HTTP request.
    add_args:
        Arguments to add_message.

    Returns
    -------
    message
        The message added.
    """
    message = assert_good_response(response)
    assert message["is_valid"]
    assert message["parent_id"] is None
    assert message["date_invalidated"] is None
    for key, value in add_args.items():
        if key == "is_new":
            continue  # Not part of the message
        assert message[key] == add_args[key]
    return message


class AddMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_add_message(self) -> None:
        repo_path = pathlib.Path(__file__).parent / "data" / "LSSTCam"
        repo_path_2 = pathlib.Path(__file__).parent / "data" / "LATISS"

        async with create_test_client(
            repo_path=repo_path, repo_path_2=repo_path_2, num_messages=0
        ) as (
            client,
            messages,
        ):
            # Add a message whose obs_id matches an exposure
            # and with all test tags and URLs in random order.
            shuffled_test_tags = TEST_TAGS[:]
            random.shuffle(shuffled_test_tags)
            shuffled_test_urls = TEST_URLS[:]
            random.shuffle(shuffled_test_urls)
            add_args = dict(
                obs_id="MC_C_20190322_000002",
                instrument="LSSTCam",
                message_text="A sample message",
                level=10,
                tags=shuffled_test_tags,
                urls=shuffled_test_urls,
                user_id="test_add_message",
                user_agent="pytest",
                is_human=False,
                is_new=False,
                exposure_flag="none",
            )
            for suffix in ("", "/"):
                response = await client.post(
                    "/exposurelog/messages" + suffix, json=add_args
                )
                assert_good_add_response(response=response, add_args=add_args)

            # Add a message whose obs_id does not match an exposure,
            # and ``is_new=True``. This should succeed, with data_added = now.
            current_time = astropy.time.Time.now()
            no_obs_id_args = add_args.copy()
            no_obs_id_args["obs_id"] = random_obs_id()
            no_obs_id_args["is_new"] = True
            response = await client.post(
                "/exposurelog/messages",
                json=no_obs_id_args,
            )
            message = assert_good_add_response(
                response=response, add_args=no_obs_id_args
            )
            assert message["date_added"] > current_time.tai.isot

            # Error: add a message whose obs_id does not match an exposure,
            # and ``is_new=False``.
            no_obs_id_args["is_new"] = False
            response = await client.post(
                "/exposurelog/messages",
                json=no_obs_id_args,
            )
            assert response.status_code == http.HTTPStatus.NOT_FOUND

            # Error: add a message with is_new true and invalid obs_id
            bad_obs_id_args = add_args.copy()
            bad_obs_id_args["is_new"] = True
            good_day_obs = str(current_date_and_day_obs()[1])
            good_seq_num = "123456"
            for bad_fields in (
                ("A",),  # 1 of 4 fields
                ("A", good_day_obs),  # 2 of 4 fields
                ("A", good_day_obs, good_seq_num),  # 3 of 4 fields
                ("AA", "A", "EXTRA", good_day_obs, good_seq_num),
                ("A", "A", good_day_obs, good_seq_num),
                ("aa", "A", good_day_obs, good_seq_num),
                ("AAA", "A", good_day_obs, good_seq_num),
                ("AA", "", good_day_obs, good_seq_num),
                ("AA", "a", good_day_obs, good_seq_num),
                ("AA", "AA", good_day_obs, good_seq_num),
                ("AA", "A", str(int(good_day_obs) + 3), good_seq_num),
                ("AA", "A", str(int(good_day_obs) - 3), good_seq_num),
                ("AA", "A", "2023123", good_seq_num),
                ("A", "A", good_day_obs, "12345"),
                ("A", "A", good_day_obs, "a23456"),
                ("A", "A", good_day_obs, "1234567"),
            ):
                bad_obs_id_args["obs_id"] = "_".join(bad_fields)
                response = await client.post(
                    "/exposurelog/messages",
                    json=bad_obs_id_args,
                )
                assert response.status_code == http.HTTPStatus.BAD_REQUEST

            # Error: add a message with invalid tags.
            invalid_tags = [
                "not valid",
                "also=not=valid",
                "again?",
            ]
            for num_invalid_tags in range(1, len(invalid_tags)):
                for num_valid_tags in range(2):
                    some_valid_tags = random.sample(TEST_TAGS, num_valid_tags)
                    some_invalid_tags = random.sample(
                        invalid_tags, num_invalid_tags
                    )
                    tags_list = some_valid_tags + some_invalid_tags
                    random.shuffle(tags_list)
                    bad_tags_args = add_args.copy()
                    bad_tags_args["tags"] = tags_list
                    response = await client.post(
                        "/exposurelog/messages",
                        json=bad_tags_args,
                    )
                    assert response.status_code == http.HTTPStatus.BAD_REQUEST

            # Error: add a message that is missing a required parameter.
            # This is a schema violation. The error code is 422,
            # but I have not found that documented,
            # so accept anything in the 400s.
            optional_fields = frozenset(
                ["level", "tags", "urls", "exposure_flag", "is_new"]
            )
            for key in add_args:
                if key in optional_fields:
                    continue
                bad_add_args = add_args.copy()
                del bad_add_args[key]
                response = await client.post(
                    "/exposurelog/messages", json=bad_add_args
                )
                assert 400 <= response.status_code < 500
