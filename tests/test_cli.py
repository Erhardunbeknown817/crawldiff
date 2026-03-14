"""Tests for CLI entry point."""

from __future__ import annotations

from typer.testing import CliRunner

from crawldiff import __version__
from crawldiff.cli import app

runner = CliRunner()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    assert "crawldiff" in result.output
