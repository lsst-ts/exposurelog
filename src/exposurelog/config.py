"""Configuration definition."""

__all__ = ["Configuration"]

import os
from dataclasses import dataclass


@dataclass
class Configuration:
    """Configuration for exposurelog."""

    # List a default value for this required parameter to make mypi happy.
    # It probably better than using Optional[str] for a required parameter.
    butler_uri_1: str = os.getenv("BUTLER_URI_1", "")
    """URI for a butler registry. Required.

    Set with the ```BUTLER_URI_1``` environment variable.
    """

    butler_uri_2: str = os.getenv("BUTLER_URI_2", "")
    """URI for a second butler registry, or "" if none.

    Set with the ```BUTLER_URI_2``` environment variable.
    """

    exposurelog_db_user: str = os.getenv("EXPOSURELOG_DB_USER", "exposurelog")
    """Exposure log database user name."""

    exposurelog_db_password: str = os.getenv("EXPOSURELOG_DB_PASSWORD", "")
    """Exposure log database password."""

    exposurelog_db_host: str = os.getenv("EXPOSURELOG_DB_HOST", "localhost")
    """Exposure log database server host."""

    exposurelog_db_port: str = os.getenv("EXPOSURELOG_DB_PORT", "5432")
    """Exposure log database server port."""

    exposurelog_db_database: str = os.getenv(
        "EXPOSURELOG_DB_DATABASE", "exposurelog"
    )
    """Exposure log database name."""

    site_id: str = os.getenv("SITE_ID", "")
    """Site ID (required).

    Requirements:

    * It must be specified and not blank.
    * It must be different for each exposure log deployment
      (and thus each instance of the exposure log database)
      in order for messages to be synchronized between databases.
    * Its length must be <= exposurelog.create_messages_table.SITE_ID_LEN.
    """

    name: str = os.getenv("SAFIR_NAME", "exposurelog")
    """The application's name, which doubles as the root HTTP endpoint path.

    Set with the ``SAFIR_NAME`` environment variable.
    """

    profile: str = os.getenv("SAFIR_PROFILE", "development")
    """Application run profile: "development" or "production".

    Set with the ``SAFIR_PROFILE`` environment variable.
    """

    logger_name: str = os.getenv("SAFIR_LOGGER", "exposurelog")
    """The root name of the application's logger.

    Set with the ``SAFIR_LOGGER`` environment variable.
    """

    log_level: str = os.getenv("SAFIR_LOG_LEVEL", "INFO")
    """The log level of the application's logger.

    Set with the ``SAFIR_LOG_LEVEL`` environment variable.
    """
