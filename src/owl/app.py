"""The main application definition for owl service."""

__all__ = ["create_app"]

import pathlib
import typing

import jsonschema
import yaml
from aiohttp import web
from lsst.daf.butler import Butler
from safir.http import init_http_session
from safir.logging import configure_logging
from safir.metadata import setup_metadata
from safir.middleware import bind_logger

from owl.config import Configuration
from owl.handlers import init_external_routes, init_internal_routes
from owl.owl_database import OwlDatabase


def create_app(**configs: typing.Any) -> web.Application:
    """Create and configure the aiohttp.web application."""
    config = Configuration(**configs)
    configure_logging(
        profile=config.profile,
        log_level=config.log_level,
        name=config.logger_name,
    )

    owl_db = OwlDatabase(config.owl_database_url)
    if not config.butler_uri_1:
        raise ValueError("Must specify BUTLER_URI_1")
    # Use str(...) around the butler URIs to support pathlib.Path paths.
    butlers = [Butler(str(config.butler_uri_1), writeable=False)]
    if config.butler_uri_2:
        butlers.append(Butler(str(config.butler_uri_2), writeable=False))

    # build command schema validators
    schemas_dir = pathlib.Path(__file__).parents[2] / "schemas"
    validators = dict()
    for name in ("add", "delete", "edit"):
        with open(schemas_dir / f"{name}.yaml", "r") as f:
            schema_dict = yaml.safe_load(f.read())
            validators[name] = jsonschema.Draft7Validator(schema_dict)

    root_app = web.Application()
    root_app["safir/config"] = config
    root_app["owl/owl_database"] = owl_db
    root_app["owl/registries"] = [butler.registry for butler in butlers]
    root_app["owl/validators"] = validators
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
