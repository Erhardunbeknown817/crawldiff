"""Tests for the config commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.exceptions import Exit

from crawldiff.commands.config import config_get, config_set, config_show


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    return tmp_path / ".crawldiff"


@pytest.fixture(autouse=True)
def _patch_paths(config_dir: Path) -> None:  # type: ignore[misc]
    config_path = config_dir / "config.json"
    with (
        patch("crawldiff.utils.config.CRAWLDIFF_DIR", config_dir),
        patch("crawldiff.utils.config.CONFIG_PATH", config_path),
    ):
        yield


def test_config_set_valid_key():
    with patch("crawldiff.commands.config.print_success") as mock_success:
        config_set("ai.provider", "anthropic")
    mock_success.assert_called_once()
    assert "ai.provider" in mock_success.call_args[0][0]


def test_config_set_invalid_key():
    with (
        patch("crawldiff.commands.config.print_error") as mock_error,
        pytest.raises(Exit),
    ):
        config_set("invalid.key", "value")
    mock_error.assert_called_once()
    assert "Unknown config key" in mock_error.call_args[0][0]


def test_config_set_masks_tokens():
    with patch("crawldiff.commands.config.print_success") as mock_success:
        config_set("cloudflare.api_token", "super-secret-token-1234")
    assert "****1234" in mock_success.call_args[0][0]
    assert "super-secret-token-1234" not in mock_success.call_args[0][0]


def test_config_get_existing_value():
    config_set("ai.provider", "openai")
    with patch("crawldiff.commands.config.typer.echo") as mock_echo:
        config_get("ai.provider")
    mock_echo.assert_called_once_with("openai")


def test_config_get_missing_value():
    with (
        patch("crawldiff.commands.config.print_error"),
        pytest.raises(Exit),
    ):
        config_get("ai.model")


def test_config_show():
    config_set("ai.provider", "anthropic")
    with patch("crawldiff.commands.config.print_config_table") as mock_table:
        config_show()
    mock_table.assert_called_once()
    flat = mock_table.call_args[0][0]
    assert isinstance(flat, dict)
    assert "ai.provider" in flat
