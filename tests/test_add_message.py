from __future__ import annotations

import pathlib
import unittest

import astropy.time
import httpx

from exposurelog.testutils import (
    MessageDictT,
    assert_good_response,
    create_test_client,
)


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
    assert message["date_is_valid_changed"] is None
    for key, value in add_args.items():
        if key == "is_new":
            continue  # Not part of the message
        assert message[key] == add_args[key]
    return message


class AddMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_add_message(self) -> None:
        """Test adding a message."""
        repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
        async with create_test_client(repo_path=repo_path, num_messages=0) as (
            client,
            messages,
        ):

            # Add a message whose obs_id matches an exposure.
            add_args = dict(
                obs_id="HSCA90333600",
                instrument="HSC",
                message_text="A sample message",
                user_id="test_add_message",
                user_agent="pytest",
                is_human=False,
                is_new=False,
                exposure_flag="none",
            )
            response = await client.post(
                "/exposurelog/add_message/", data=add_args
            )
            assert_good_add_response(response=response, add_args=add_args)

            # Add a message whose obs_id does not match an exposure,
            # and ``is_new=True``. This should succeed, with data_added = now.
            current_time = astropy.time.Time.now()
            no_obs_id_args = add_args.copy()
            no_obs_id_args["obs_id"] = "NO_SUCH_OBS_ID"
            no_obs_id_args["is_new"] = True
            response = await client.post(
                "/exposurelog/add_message/",
                data=no_obs_id_args,
            )
            message = assert_good_add_response(
                response=response, add_args=no_obs_id_args
            )
            assert message["date_added"] > current_time.tai.iso

            # Error: add a message whose obs_id does not match an exposure,
            # and ``is_new=False``.
            no_obs_id_args["is_new"] = False
            response = await client.post(
                "/exposurelog/add_message/",
                data=no_obs_id_args,
            )
            assert response.status_code == 404

            # Error: add a message that is missing a required field.
            # This is a schema violation so the error code is 422,
            # but I have not found that documented so
            # accept anything in the 400s
            for key in add_args:
                if key in ("exposure_flag", "is_new"):
                    continue  # Optional field
                bad_add_args = add_args.copy()
                del bad_add_args[key]
                response = await client.post(
                    "/add_message/", data=bad_add_args
                )
                assert 400 <= response.status_code < 500
