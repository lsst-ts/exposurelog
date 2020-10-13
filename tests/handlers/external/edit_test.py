"""Tests for the owl.handlers.external.index module and routes."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import testing.postgresql
from sqlalchemy import create_engine

from owl.app import create_app
from owl.create_messages_table import create_messages_table

if TYPE_CHECKING:
    from aiohttp.pytest_plugin.test_utils import TestClient


async def test_edit_message(aiohttp_client: TestClient) -> None:
    """Test editing a message."""
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

        # Add a message.
        old_data = dict(
            obs_id="HSCA90333600",
            instrument="HSC",
            message_text="A sample message",
            user_id="test_edit_message",
            user_agent="pytest",
            is_human=False,
            exposure_flag="questionable",
        )
        response = await client.get(f"/{name}/add", json=old_data)
        assert response.status == 200
        data = await response.json()
        old_message_id = data["id"]

        # Edit the message
        full_new_data = dict(
            id=old_message_id,
            message_text="New message text",
            user_id="new user_id",
            user_agent="new user_agent",
            is_human=True,
            exposure_flag="junk",
        )
        # Add a new version of the message with one field omitted
        # to check that one field is not changed from the original
        for del_key in full_new_data:
            if del_key == "id":
                continue  # id is required
            new_data = full_new_data.copy()
            del new_data[del_key]
            response = await client.get(f"/{name}/edit", json=new_data)
            assert response.status == 200
            data = await response.json()
            assert data["parent_id"] == old_message_id
            assert data["is_valid"]
            assert data["date_is_valid_changed"] is None
            for key in full_new_data:
                if key == "id":
                    assert data[key] != old_message_id
                elif key == del_key:
                    assert data[key] == old_data[key]
                else:
                    assert data[key] == new_data[key]

        # Error: must specify "id"
        bad_new_data = new_data.copy()
        del bad_new_data["id"]
        response = await client.get(f"/{name}/edit", json=bad_new_data)
        assert response.status == 500

        # Error: edit a message that does not exist.
        bad_new_data = new_data.copy()
        bad_new_data["id"] = 9999
        response = await client.get(f"/{name}/edit", json=bad_new_data)
        assert response.status == 500
