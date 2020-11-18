"""The main application definition for exposurelog service."""

__all__ = ["create_app"]

import typing

from aiohttp import web
from graphql_server.aiohttp import GraphQLView
from lsst.daf.butler import Butler
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger

from exposurelog.config import Configuration
from exposurelog.handlers import init_external_routes, init_internal_routes
from exposurelog.log_message_database import LogMessageDatabase
from exposurelog.schemas.app_schema import app_schema


def create_app(**configs: typing.Any) -> web.Application:
    """Create and configure the aiohttp.web application."""
    config = Configuration(**configs)
    configure_logging(
        profile=config.profile,
        log_level=config.log_level,
        name=config.logger_name,
    )

    if not config.butler_uri_1:
        raise ValueError("Must specify BUTLER_URI_1")
    # Use str(...) around the butler URIs to support pathlib.Path paths.
    butlers = [Butler(str(config.butler_uri_1), writeable=False)]
    if config.butler_uri_2:
        butlers.append(Butler(str(config.butler_uri_2), writeable=False))

    async def startup(app: web.Application) -> None:
        """Create and start LogMessageDatabase.

        When the app is created there is no event loop, so LogMessageDatabase
        cannot be created and started in the main body of this code.
        See https://docs.aiohttp.org/en/v2.3.3/web.html#background-tasks
        """
        exposurelog_db = LogMessageDatabase(config.exposure_log_database_url)
        root_app["exposurelog/exposure_log_database"] = exposurelog_db

    async def cleanup(app: web.Application) -> None:
        exposurelog_db = root_app["exposurelog/exposure_log_database"]
        await exposurelog_db.close()

    root_app = web.Application()
    root_app.on_startup.append(startup)
    root_app.on_cleanup.append(cleanup)
    root_app["safir/config"] = config
    root_app["exposurelog/registries"] = [
        butler.registry for butler in butlers
    ]
    setup_metadata(package_name="exposurelog", app=root_app)
    setup_middleware(root_app)
    root_app.add_routes(init_internal_routes())
    root_app.cleanup_ctx.append(init_http_session)

    GraphQLView.attach(
        root_app,
        schema=app_schema,
        route_path="/exposurelog/graphql",
        root_value=root_app,
        enable_async=True,
        graphiql=True,
    )

    sub_app = web.Application()
    setup_middleware(sub_app)
    sub_app.add_routes(init_external_routes())
    root_app.add_subapp(f'/{root_app["safir/config"].name}', sub_app)

    return root_app


def setup_middleware(app: web.Application) -> None:
    """Add middleware to the application."""
    app.middlewares.append(bind_logger)
