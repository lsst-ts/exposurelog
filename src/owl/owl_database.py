"""Configuration definition."""

__all__ = ["OwlDatabase"]

import asyncio

import aiopg
import aiopg.sa
import structlog

from owl.create_messages_table import create_messages_table


class OwlDatabase:
    """Connection to the OWL database and message table.

    Parameters
    ----------
    url
        URL of OWL database server in the form:
        postgresql://[user[:password]@][netloc][:port][/dbname]
    table
        Name of table holding OWL messages.
    """

    def __init__(self, url: str, table: str = "owl_messages"):
        self._closed = False
        self.url = url
        self.table = table
        self.connection = None
        self.logger = structlog.get_logger("OwlDatabase")
        self.engine = None
        self.table = create_messages_table(create_indices=False)
        self.start_task = asyncio.create_task(self.start())

    async def start(self):
        self.logger.info("Create engine")
        self.engine = await aiopg.sa.create_engine(self.url)

    def basic_close(self):
        """Minimal close. Call this if you have no event loop."""
        if self._closed:
            return
        self._closed = True
        if self.engine is not None:
            self.engine.terminate()

    async def close(self):
        """Full close. Call this if you have an event loop."""
        if self._closed:
            return
        self._closed = True
        if self.engine is not None:
            self.engine.terminate()
            await self.engine.wait_closed()

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.close()
