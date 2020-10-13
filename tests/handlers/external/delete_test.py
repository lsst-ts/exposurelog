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
) -> dict:
    """Check the response from a successful add.

    Return the data as a dict.
    """
    assert response.status == 200
    data = await response.json()
    assert not data["is_valid"]
    assert data["parent_id"] is None
    assert data["date_is_valid_changed"] is not None
    for key, value in add_data.items():
        if key in "is_new":
            continue  # Not part of the message
        assert data[key] == add_data[key]
    return data


async def test_delete_message(aiohttp_client: TestClient) -> None:
    """Test adding a message."""
    repo_path = pathlib.Path(__file__).parents[2] / "data" / "hsc_raw"
    with testing.postgresql.Postgresql() as postgresql:
        # connect to PostgreSQL
        engine = create_engine(postgresql.url())

        table = create_messages_table(create_indices=False)
        table.metadata.create_all(engine)

        app = create_app(
            owl_database_url=postgresql.url(), butler_uri_1=repo_path
        )
        name = app["safir/config"].name
        client = await aiohttp_client(app)

        # Add a message, so we have one to delete
        add_data = dict(
            obs_id="HSCA90333600",
            instrument="HSC",
            message_text="A sample message",
            user_id="test_delete_message",
            user_agent="pytest",
            is_human=False,
            exposure_flag="questionable",
        )
        response = await client.get(f"/{name}/add", json=add_data)
        assert response.status == 200
        data = await response.json()
        message_id = data["id"]

        # Delete the message
        response = await client.get(
            f"/{name}/delete", json=dict(id=message_id)
        )
        assert response.status == 200
        data = await assert_good_response(response=response, add_data=add_data)

        # Delete the same message again.
        # This should update row.date_is_valid_changed
        response = await client.get(
            f"/{name}/delete", json=dict(id=message_id)
        )
        assert response.status == 200
        data2 = await assert_good_response(
            response=response, add_data=add_data
        )
        assert data2["date_is_valid_changed"] > data["date_is_valid_changed"]

        # Error: delete a message that does not exist.
        response = await client.get(f"/{name}/delete", json=dict(id=9999))
        assert response.status == 500
