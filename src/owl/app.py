"""The main application definition for owl service."""

__all__ = ["create_app"]

from aiohttp import web
from lsst.daf.butler import Butler
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger

from owl.config import Configuration
from owl.handlers import init_external_routes, init_internal_routes
from owl.owl_database import OwlDatabase


def create_app() -> web.Application:
    """Create and configure the aiohttp.web application."""
    config = Configuration()
    configure_logging(
        profile=config.profile,
        log_level=config.log_level,
        name=config.logger_name,
    )

    print(f"butler_uri_1 = {config.butler_uri_1}")
    print(f"butler_uri_2 = {config.butler_uri_2}")
    print(f"owl_database_url = {config.owl_database_url}")
    owl_db = OwlDatabase(config.owl_database_url)
    if not config.butler_uri_1:
        raise ValueError("Must specify BUTLER_URI_1")
    butlers = [Butler(config.butler_uri_1, writeable=False)]
    if config.butler_uri_2:
        butlers.append(Butler(config.butler_uri_2, writeable=False))

    root_app = web.Application()
    root_app["safir/config"] = config
    root_app["owl/owl_database"] = owl_db
    root_app["owl/butlers"] = butlers
    setup_metadata(package_name="owl", app=root_app)
    setup_middleware(root_app)
    root_app.add_routes(init_internal_routes())
    root_app.cleanup_ctx.append(init_http_session)

    sub_app = web.Application()
    setup_middleware(sub_app)
    sub_app.add_routes(init_external_routes())
    root_app.add_subapp(f'/{root_app["safir/config"].name}', sub_app)

    return root_app


def setup_middleware(app: web.Application) -> None:
    """Add middleware to the application."""
    app.middlewares.append(bind_logger)
