from __future__ import annotations

__all__ = ["create_shared_state", "delete_shared_state", "get_shared_state"]

import logging
import os
import urllib.parse

import lsst.daf.butler

from .create_message_table import SITE_ID_LEN, create_message_table
from .log_message_database import LogMessageDatabase

_shared_state: None | SharedState = None


def get_env(name: str, default: None | str = None) -> str:
    """Get a value from an environment variable.

    Parameters
    ----------
    name
        The name of the environment variable.
    default
        The default value; if None then raise ValueError if absent.
    """
    if default is not None and not isinstance(default, str):
        raise ValueError(f"default={default!r} must be a str or None")
    value = os.environ.get(name, default)
    if value is None:
        raise ValueError(f"You must specify environment variable {name}")
    return value


def create_db_url() -> str:
    """Create the exposurelog database URL from environment variables."""
    exposurelog_db_user = get_env("EXPOSURELOG_DB_USER", "exposurelog")
    exposurelog_db_password = get_env("EXPOSURELOG_DB_PASSWORD", "")
    exposurelog_db_host = get_env("EXPOSURELOG_DB_HOST", "localhost")
    exposurelog_db_port = int(get_env("EXPOSURELOG_DB_PORT", "5432"))
    exposurelog_db_database = get_env("EXPOSURELOG_DB_DATABASE", "exposurelog")
    encoded_db_password = urllib.parse.quote_plus(exposurelog_db_password)
    return (
        f"postgresql+asyncpg://{exposurelog_db_user}:{encoded_db_password}"
        f"@{exposurelog_db_host}:{exposurelog_db_port}"
        f"/{exposurelog_db_database}"
    )


class SharedState:
    """Shared application state.

    All attributes are set by environment variables.

    Attributes
    ----------
    site_id : str
        Name identifying where the exposurelog service is running.
        Values include: "summit" and "base".
    butler_uri_1 (required)
        URI for a butler registry.
    butler_uri_2
        URI for a second butler registry, or "" if none.
    ...
    butler_uri_{num_registries}
        URIs for additional regitries.
    registries : list[lsst.daf.butler.Registry]
        List of one or two butler registries.
    exposurelog_db : sa.Table

    Notes
    -----
    Reads the following env variables; all are optional,
    unless otherwise noted:

    SITE_ID (required)
        String identifying where the exposurelog service is running.
        Standard values include: "summit" and "base".
    BUTLER_URI_1 (required)
        URI for a butler registry.
    BUTLER_URI_2
        URI for a second butler registry, or "" if none.
    ...
    BUTLER_URI_{num_registries}
        URIs for additional regitries.
    EXPOSURELOG_DB_USER
        Exposure log database user name.
    EXPOSURELOG_DB_PASSWORD
        Exposure log database password.
    EXPOSURELOG_DB_HOST
        Exposure log database TCP/IP host.
    EXPOSURELOG_DB_PORT
        Exposure log database TCP/IP port.
    EXPOSURELOG_DB_DATABASE
        Name of exposurelog database.
    """

    # How many butler registries to read?
    # This also controls how many butler_uri_n attributes there are.
    # If you change this value then also update the following:
    # * Config in get_configuration.py.
    # * create_test_client in testutils.py.
    # * The exposurelog deployment files in the phalanx package.
    num_registries = 3

    def __init__(self) -> None:
        site_id = get_env("SITE_ID")
        if len(site_id) > SITE_ID_LEN:
            raise ValueError(
                f"SITE_ID={site_id!r} too long; max length={SITE_ID_LEN}"
            )

        self.registries: list[lsst.daf.butler.Registry] = []
        for i in range(self.num_registries):
            uri_attr_name = f"butler_uri_{i + 1}"
            # The first butler URI is required.
            default = None if i == 0 else ""
            butler_uri = get_env(uri_attr_name.upper(), default=default)
            setattr(self, uri_attr_name, butler_uri)
            if butler_uri != "":
                butler = lsst.daf.butler.Butler(butler_uri)
                self.registries.append(butler.registry)
        exposurelog_db_url = create_db_url()

        self.log = logging.getLogger("exposurelog")
        self.site_id = site_id
        self.exposurelog_db = LogMessageDatabase(
            message_table=create_message_table(), url=exposurelog_db_url
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
