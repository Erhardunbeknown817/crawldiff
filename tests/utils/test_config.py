"""Tests for configuration management."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crawldiff.utils.config import (
    ConfigError,
    get_cloudflare_credentials,
    get_value,
    load_config,
    mask_secret,
    save_config,
    set_value,
)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Temporary config directory."""
    return tmp_path / ".crawldiff"


@pytest.fixture(autouse=True)
def _patch_paths(config_dir: Path) -> None:  # type: ignore[misc]
    """Redirect config paths to temp directory."""
    config_path = config_dir / "config.json"
    with (
        patch("crawldiff.utils.config.CRAWLDIFF_DIR", config_dir),
        patch("crawldiff.utils.config.CONFIG_PATH", config_path),
    ):
        yield


def test_load_config_returns_defaults():
    config = load_config()
    assert "cloudflare" in config
    assert "ai" in config
    assert "defaults" in config


def test_set_and_get_value():
    set_value("ai.provider", "anthropic")
    assert get_value("ai.provider") == "anthropic"


def test_get_value_missing_key():
    assert get_value("nonexistent.key") == ""


def test_env_var_takes_precedence():
    set_value("cloudflare.account_id", "from-file")
    with patch.dict("os.environ", {"CLOUDFLARE_ACCOUNT_ID": "from-env"}):
        assert get_value("cloudflare.account_id") == "from-env"


def test_save_and_load_config(config_dir: Path):
    config = {"cloudflare": {"account_id": "test-123"}}
    save_config(config)
    loaded = load_config()
    assert loaded["cloudflare"]["account_id"] == "test-123"


def test_get_cloudflare_credentials():
    set_value("cloudflare.account_id", "my-account")
    set_value("cloudflare.api_token", "my-token")
    account_id, api_token = get_cloudflare_credentials()
    assert account_id == "my-account"
    assert api_token == "my-token"


def test_get_cloudflare_credentials_missing():
    """Credentials check with empty values should raise."""
    set_value("cloudflare.account_id", "")
    set_value("cloudflare.api_token", "")
    with patch.dict("os.environ", {}, clear=True), pytest.raises(ConfigError):
        get_cloudflare_credentials()


def test_mask_secret_long():
    assert mask_secret("super-secret-token-1234") == "****1234"


def test_mask_secret_short():
    assert mask_secret("abc") == "****"


def test_mask_secret_exactly_four():
    assert mask_secret("abcd") == "****"


def test_anthropic_api_key_env_fallback():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        assert get_value("ai.api_key") == "sk-ant-test"


def test_openai_api_key_env_fallback():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-oai-test"}):
        assert get_value("ai.api_key") == "sk-oai-test"


def test_crawldiff_ai_key_takes_precedence_over_provider_keys():
    with patch.dict("os.environ", {
        "CRAWLDIFF_AI_API_KEY": "crawldiff-key",
        "ANTHROPIC_API_KEY": "anthropic-key",
    }):
        assert get_value("ai.api_key") == "crawldiff-key"
