"""Configuration definition."""

__all__ = ["OwlDatabase"]

import asyncio

import aiopg


class OwlDatabase:
    """Connection to the OWL message database.

    Parameters
    ----------
    url : `str`
        URL of OWL database server in the form:
        postgresql://[user[:password]@][netloc][:port][/dbname]
    """

    def __init__(self, url, table="owl_messages"):
        self._closed = False
        self.url = url
        self.table = table
        self.connection = None
        self.start_task = asyncio.create_task(self.start())

    async def start(self):
        print("OwlDatabase: connecting")
        self.connection = await aiopg.connect(self.url)
        print("OwlDatabase: connected")

    def basic_close(self):
        """Minimal close. Call this if you have no event loop."""
        if self._closed:
            return
        self._closed = True
        if self.connection is not None:
            self.connection.close()

    async def close(self):
        """Full close. Call this if you have an event loop."""
        if self._closed:
            return
        self._closed = True
        if self.connection is not None:
            self.connection.close()
            await self.connection.wait_closed()

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.close()
