"""Tests for the owl.handlers.external.index module and routes."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import aiohttp
import testing.postgresql
from sqlalchemy import create_engine

from owl.app import create_app
from owl.create_messages_table import create_messages_table

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


async def assert_good_response(
    response: aiohttp.ClientResponse, add_data: dict
):
    """Check the response from a successful add."""
    assert response.status == 200
    data = await response.json()
    assert data["is_valid"]
    assert data["parent_id"] is None
    assert data["date_is_valid_changed"] is None
    for key, value in add_data.items():
        if key == "is_new":
            continue  # Not part of the message
        assert data[key] == add_data[key]


async def test_add_message(aiohttp_client: TestClient) -> None:
    """Test adding a message."""
    repo_path = pathlib.Path(__file__).parents[2] / "data" / "hsc_raw"
    with testing.postgresql.Postgresql() as postgresql:
        # connect to PostgreSQL
        engine = create_engine(postgresql.url())

        table = create_messages_table(create_indices=True)
        table.metadata.create_all(engine)

        app = create_app(
            owl_database_url=postgresql.url(), butler_uri_1=repo_path
        )
        name = app["safir/config"].name
        client = await aiohttp_client(app)

        # Add a message that should succeed
        add_data = dict(
            obs_id="HSCA90333600",
            instrument="HSC",
            message_text="A sample message",
            user_id="test_add_message",
            user_agent="pytest",
            is_human=False,
            is_new=False,
            exposure_flag="questionable",
        )
        response = await client.get(f"/{name}/add", json=add_data)
        await assert_good_response(response=response, add_data=add_data)

        # Add a message with no such obs_id and is_new True
        no_obs_id_data = add_data.copy()
        no_obs_id_data["obs_id"] = "NO_SUCH_OBS_ID"
        no_obs_id_data["is_new"] = True
        response = await client.get(f"/{name}/add", json=no_obs_id_data)
        await assert_good_response(response=response, add_data=no_obs_id_data)

        # Error: add a message with no such obs_id and is_new False
        no_obs_id_data["is_new"] = False
        response = await client.get(f"/{name}/add", json=no_obs_id_data)
        assert response.status == 500

        # Error: add a message that is missing a required field.
        for key in add_data:
            if key in ("exposure_flag", "is_new"):
                continue  # Optional field
            bad_add_data = add_data.copy()
            del bad_add_data[key]
            response = await client.get(f"/{name}/add", json=bad_add_data)
            assert response.status == 500
