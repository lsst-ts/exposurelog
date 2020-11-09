from __future__ import annotations

"""Configuration definition."""

__all__ = ["LogMessageDatabase"]

import asyncio
import typing

import aiopg
import aiopg.sa
import structlog

if typing.TYPE_CHECKING:
    import sqlalchemy as sa

from explog.create_messages_table import create_messages_table


class LogMessageDatabase:
    """Connection to the exposure log database and message table.

    Parameters
    ----------
    url
        URL of exposure log database server in the form:
        postgresql://[user[:password]@][netloc][:port][/dbname]
    """

    def __init__(self, url: str):
        self._closed = False
        self.url = url
        self.logger = structlog.get_logger("LogMessageDatabase")
        # Asynchronous database engine;
        # None until ``start_task`` is done.
        self._engine: typing.Optional[aiopg.sa.Engine] = None
        # A model of the database table.
        self.table: sa.Table = create_messages_table()
        # Set done when the engine has been created.
        self.start_task = asyncio.create_task(self.start())

    async def start(self) -> None:
        """Create the engine used to query the database."""
        self.logger.info("Create engine")
        self._engine = await aiopg.sa.create_engine(self.url)

    def basic_close(self) -> None:
        """Minimal close. Call this if you have no event loop."""
        if self._closed:
            return
        self._closed = True
        self.start_task.cancel()
        if self._engine is not None:
            self._engine.terminate()

    @property
    def engine(self) -> aiopg.sa.Engine:
        if self._engine is None:
            raise RuntimeError("Not connected to the log message database.")
        return self._engine

    async def close(self) -> None:
        """Full close. Call this if you have an event loop."""
        if self._closed:
            return
        self._closed = True
        self.start_task.cancel()
        if self._engine is not None:
            self._engine.terminate()
            await self._engine.wait_closed()

    async def __aenter__(self) -> LogMessageDatabase:
        return self

    async def __aexit__(self, *args: typing.Any) -> None:
        await self.close()
