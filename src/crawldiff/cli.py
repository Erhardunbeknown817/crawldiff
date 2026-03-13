"""Main CLI entry point for crawldiff.

All commands are registered here. This is the only file that
imports from commands/ — keeping the dependency tree clean.
"""

from __future__ import annotations

import typer
from rich.console import Console

from crawldiff import __version__
from crawldiff.commands.config import config_app
from crawldiff.commands.crawl import crawl
from crawldiff.commands.diff import diff
from crawldiff.commands.history import history
from crawldiff.commands.watch import watch

app = typer.Typer(
    name="crawldiff",
    help="git log for any website — AI-powered website change tracking.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)

# Register sub-commands
app.command("crawl", help="Crawl a website and store a snapshot locally.")(crawl)
app.command("diff", help="Show what changed on a website since the last crawl.")(diff)
app.command("history", help="List all crawl snapshots for a site.")(history)
app.command("watch", help="Watch a site and report changes on each interval.")(watch)
app.add_typer(config_app, name="config")


def version_callback(value: bool) -> None:
    if value:
        Console().print(f"crawldiff [bold]{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback,
        is_eager=True, help="Show version and exit.",
    ),
) -> None:
    """crawldiff — git log for any website."""
