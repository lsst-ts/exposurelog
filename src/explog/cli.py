"""Administrative command-line interface."""

__all__ = ["main", "help", "run"]

from typing import Any, Union

import click
import sqlalchemy as sa
from aiohttp.web import run_app

from explog.app import create_app
from explog.config import Configuration
from explog.create_messages_table import create_messages_table

# Add -h as a help shortcut option
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(message="%(version)s")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Exposure log administrative command-line interface."""
    # Subcommands should use the click.pass_obj decorator to get this
    # ctx object as the first argument.
    ctx.obj = {}


@main.command()
@click.argument("topic", default=None, required=False, nargs=1)
@click.pass_context
def help(ctx: click.Context, topic: Union[None, str], **kw: Any) -> None:
    """Show help for any command."""
    # The help command implementation is taken from
    # https://www.burgundywall.com/post/having-click-help-subcommand
    if topic:
        if topic in main.commands:
            ctx.info_name = topic
            click.echo(main.commands[topic].get_help(ctx))
        else:
            raise click.UsageError(f"Unknown help topic {topic}", ctx)
    else:
        assert ctx.parent
        click.echo(ctx.parent.get_help())


@main.command()
@click.option(
    "--port", default=8080, type=int, help="Port to run the application on."
)
@click.pass_context
def run(ctx: click.Context, port: int) -> None:
    """Run the application (for production)."""
    app = create_app()
    run_app(app, port=port)


@main.command()
@click.pass_context
def create_table(ctx: click.Context) -> None:
    """Create the log message table if it does not already exist.

    To replace an existing table, first manually drop the old table.
    """
    config = Configuration()
    engine = sa.create_engine(config.exposure_log_database_url)
    create_messages_table(engine=engine)
