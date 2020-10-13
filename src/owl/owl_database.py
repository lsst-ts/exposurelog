from __future__ import annotations

"""Configuration definition."""

__all__ = ["OwlDatabase"]

import asyncio
import typing

import aiopg
import aiopg.sa
import structlog

if typing.TYPE_CHECKING:
    import sqlalchemy

from owl.create_messages_table import create_messages_table


class OwlDatabase:
    """Connection to the OWL database and message table.

    Parameters
    ----------
    url
        URL of OWL database server in the form:
        postgresql://[user[:password]@][netloc][:port][/dbname]
    """

    def __init__(self, url: str):
        self._closed = False
        self.url = url
        self.logger = structlog.get_logger("OwlDatabase")
        # Asynchronous database engine;
        # None until ``start_task`` is done.
        self.engine: typing.Optional[aiopg.sa.Engine] = None
        # A model of the database table.
        self.table: sqlalchemy.Table = create_messages_table(
            create_indices=False
        )
        # Set done when the engine has been created.
        self.start_task = asyncio.create_task(self.start())

    async def start(self) -> None:
        """Create the engine used to query the database."""
        self.logger.info("Create engine")
        self.engine = await aiopg.sa.create_engine(self.url)

    def basic_close(self) -> None:
        """Minimal close. Call this if you have no event loop."""
        if self._closed:
            return
        self._closed = True
        if self.engine is not None:
            self.engine.terminate()

    async def close(self) -> None:
        """Full close. Call this if you have an event loop."""
        if self._closed:
            return
        self._closed = True
        if self.engine is not None:
            self.engine.terminate()
            await self.engine.wait_closed()

    async def __aenter__(self) -> OwlDatabase:
        return self

    async def __aexit__(self, *args: typing.Any) -> None:
        await self.close()
