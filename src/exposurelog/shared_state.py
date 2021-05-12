from __future__ import annotations

__all__ = ["create_shared_state", "delete_shared_state", "get_shared_state"]

import logging
import os
import typing
import urllib

import lsst.daf.butler

from . import create_message_table, log_message_database

_shared_state: typing.Optional[SharedState] = None


def get_env(name: str, default: typing.Optional[str] = None) -> str:
    if default is not None and not isinstance(default, str):
        raise ValueError(f"default={default!r} must be a str or None")
    value = os.environ.get(name, default)
    if value is None:
        raise ValueError(f"You must specify environment variable {name}")
    return value


class SharedState:
    """Shared application state.

    All attributes are set by environment variables.

    Attributes
    ----------
    site_id : str
        Name identifying where the exposurelog service is running.
        Values include: "summit" and "base".
    registries : [lsst.daf.butler.Registry]
        List of one or two butler registries.
    exposure_log_db : sa.Table

    Notes
    -----
    Reads the following env variables:

    site_id
        String identifying where the exposurelog service is running.
        Values include: "summit" and "base".
    butler_uri1
        URI for a butler registry. Required.
    butler_uri2
        URI for a second butler registry, or "" if none.
    exposurelog_db_user
        Exposure log database user name.
    exposurelog_db_password
        Exposure log database password.
    exposurelog_db_host
        Exposure log database TCP/IP host.
    exposurelog_db_port
        Exposure log database TCP/IP port.
    exposurelog_db_database
        Name of exposurelog database.
    """

    def __init__(self):  # type: ignore
        site_id = get_env("SITE_ID")
        if len(site_id) > create_message_table.SITE_ID_LEN:
            raise ValueError(
                f"SITE_ID={site_id!r} too long; "
                f"max length={create_message_table.SITE_ID_LEN}"
            )

        butler_uri_1 = get_env("BUTLER_URI_1")
        butler_uri_2 = get_env("BUTLER_URI_2", "")
        exposurelog_db_user = get_env("EXPOSURELOG_DB_USER", "exposurelog")
        exposurelog_db_password = get_env("EXPOSURELOG_DB_PASSWORD", "")
        exposurelog_db_host = get_env("EXPOSURELOG_DB_HOST", "localhost")
        exposurelog_db_port = int(get_env("EXPOSURELOG_DB_PORT", "5432"))
        exposurelog_db_database = get_env(
            "EXPOSURELOG_DB_DATABASE", "exposurelog"
        )
        encoded_db_password = urllib.parse.quote_plus(exposurelog_db_password)
        exposurelog_db_url = (
            f"postgresql://{exposurelog_db_user}:{encoded_db_password}"
            f"@{exposurelog_db_host}:{exposurelog_db_port}"
            f"/{exposurelog_db_database}"
        )

        butlers = [lsst.daf.butler.Butler(butler_uri_1, writeable=False)]
        if butler_uri_2:
            butlers.append(
                lsst.daf.butler.Butler(butler_uri_2, writeable=False)
            )

        self.log = logging.getLogger("exposurelog")
        self.site_id = site_id
        self.registries = [butler.registry for butler in butlers]
        self.exposurelog_db = log_message_database.LogMessageDatabase(
            url=exposurelog_db_url, create_table=True
        )


async def create_shared_state() -> None:
    """Create, start and then set the application shared state.

    Raises
    ------
    RuntimeError
            If the shared state has already been created.
    """
    global _shared_state
    if _shared_state is not None:
        raise RuntimeError("Shared state already created")
    state = SharedState()
    await state.exposurelog_db.start_task
    _shared_state = state


async def delete_shared_state() -> None:
    """Delete and then close the application shared state."""
    global _shared_state
    if _shared_state is None:
        return
    state = _shared_state
    _shared_state = None
    await state.exposurelog_db.close()


def get_shared_state() -> SharedState:
    """Get the application shared state.

    Raises
    ------
    RuntimeError
            If the shared state has not been created.
    """
    global _shared_state
    if _shared_state is None:
        raise RuntimeError("Shared state not created")
    return _shared_state


def has_shared_state() -> bool:
    """Has the application shared state been created?"""
    global _shared_state
    return _shared_state is not None
