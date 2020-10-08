"""Configuration definition."""

__all__ = ["Configuration"]

import os
from dataclasses import dataclass


@dataclass
class Configuration:
    """Configuration for owl."""

    name: str = os.getenv("SAFIR_NAME", "owl")
    """The application's name, which doubles as the root HTTP endpoint path.

    Set with the ``SAFIR_NAME`` environment variable.
    """

    profile: str = os.getenv("SAFIR_PROFILE", "development")
    """Application run profile: "development" or "production".

    Set with the ``SAFIR_PROFILE`` environment variable.
    """

    logger_name: str = os.getenv("SAFIR_LOGGER", "owl")
    """The root name of the application's logger.

    Set with the ``SAFIR_LOGGER`` environment variable.
    """

    log_level: str = os.getenv("SAFIR_LOG_LEVEL", "INFO")
    """The log level of the application's logger.

    Set with the ``SAFIR_LOG_LEVEL`` environment variable.
    """

    owl_database_url: str = os.getenv(
        "OWL_DATABASE_URL", "postgresql://owl@localhost/postgres"
    )
    """Path to the OWL database server containing messages.

    Set with the ``OWL_DATABASE_URL`` environment variable.
    The format is the standard postgres URL::

        postgresql://[user[:password]@][netloc][:port][/dbname]
    """

    butler_uri_1: str = os.getenv("BUTLER_URI_1")
    """URI for a butler registry.

    Set with the ```BUTLER_URI_1``` environment variable.
    """

    butler_uri_2: str = os.getenv("BUTLER_URI_2", "")
    """URI for a second butler registry, or "" if none.

    Set with the ```BUTLER_URI_2``` environment variable.
    """
