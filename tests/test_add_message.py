from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import aiohttp
import astropy.time
import testing.postgresql

from exposurelog.app import create_app
from exposurelog.testutils import (
    ArgDictT,
    MessageDictT,
    Requestor,
    assert_bad_response,
    assert_good_response,
    create_test_database,
    db_config_from_dsn,
)

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


async def assert_good_add_response(
    response: aiohttp.ClientResponse, add_args: ArgDictT
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
    message = await assert_good_response(response, command="add_message")
    assert message["is_valid"]
    assert message["parent_id"] is None
    assert message["date_is_valid_changed"] is None
    for key, value in add_args.items():
        if key == "is_new":
            continue  # Not part of the message
        assert message[key] == add_args[key]
    return message


async def test_add_message(aiohttp_client: TestClient) -> None:
    """Test adding a message."""
    repo_path = pathlib.Path(__file__).parent / "data" / "hsc_raw"
    with testing.postgresql.Postgresql() as postgresql:
        create_test_database(postgresql, num_messages=0)

        db_config = db_config_from_dsn(postgresql.dsn())
        app = create_app(**db_config, butler_uri_1=repo_path)
        name = app["safir/config"].name

        client = await aiohttp_client(app)
        await app["exposurelog/exposurelog_db"].start_task

        requestor = Requestor(
            client=client,
            category="mutation",
            command="add_message",
            url_suffix=name,
        )

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
        response = await requestor(add_args)
        await assert_good_add_response(response=response, add_args=add_args)

        # Add a message whose obs_id does not match an exposure,
        # and ``is_new=True``. This should succeed, with data_added = now.
        current_time = astropy.time.Time.now()
        no_obs_id_args = add_args.copy()
        no_obs_id_args["obs_id"] = "NO_SUCH_OBS_ID"
        no_obs_id_args["is_new"] = True
        response = await requestor(no_obs_id_args)
        message = await assert_good_add_response(
            response=response, add_args=no_obs_id_args
        )
        assert message["date_added"] > current_time.tai.iso

        # Error: add a message whose obs_id does not match an exposure,
        # and ``is_new=False``.
        no_obs_id_args["is_new"] = False
        response = await requestor(no_obs_id_args)
        await assert_bad_response(response)

        # Error: add a message that is missing a required field.
        for key in add_args:
            if key in ("exposure_flag", "is_new"):
                continue  # Optional field
            bad_add_args = add_args.copy()
            del bad_add_args[key]
            response = await requestor(bad_add_args)
            await assert_bad_response(response)
