"""Configuration management for crawldiff.

Config is stored at ~/.crawldiff/config.json.
Environment variables take precedence over config file values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CRAWLDIFF_DIR = Path.home() / ".crawldiff"
CONFIG_PATH = CRAWLDIFF_DIR / "config.json"
DB_PATH = CRAWLDIFF_DIR / "snapshots.db"

DEFAULT_CONFIG: dict[str, Any] = {
    "cloudflare": {
        "account_id": "",
        "api_token": "",
    },
    "ai": {
        "provider": "none",
        "model": "",
        "api_key": "",
    },
    "defaults": {
        "format": "markdown",
        "depth": 2,
        "max_pages": 50,
    },
}

# Env var mapping: config key → env var names (checked in order)
ENV_VARS: dict[str, list[str]] = {
    "cloudflare.account_id": ["CLOUDFLARE_ACCOUNT_ID"],
    "cloudflare.api_token": ["CLOUDFLARE_API_TOKEN"],
    "ai.api_key": ["CRAWLDIFF_AI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"],
    "ai.provider": ["CRAWLDIFF_AI_PROVIDER"],
    "ai.model": ["CRAWLDIFF_AI_MODEL"],
}


def ensure_dir() -> None:
    """Create ~/.crawldiff/ if it doesn't exist."""
    CRAWLDIFF_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load config from file, falling back to defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                stored = json.load(f)
        except (json.JSONDecodeError, OSError):
            return DEFAULT_CONFIG.copy()
        # Merge with defaults (stored values win)
        return _deep_merge(DEFAULT_CONFIG, stored)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    """Write config to disk."""
    ensure_dir()
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_value(key: str) -> str:
    """Get a config value. Env vars take precedence over file."""
    # Check env vars first (multiple fallbacks supported)
    env_vars = ENV_VARS.get(key, [])
    for env_var in env_vars:
        env_val = os.environ.get(env_var, "")
        if env_val:
            return env_val

    # Fall back to config file
    config = load_config()
    parts = key.split(".")
    current: Any = config
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return ""
    return str(current) if current else ""


def set_value(key: str, value: str) -> None:
    """Set a config value and persist to disk."""
    config = load_config()
    parts = key.split(".")
    current = config
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value
    save_config(config)


def get_cloudflare_credentials() -> tuple[str, str]:
    """Return (account_id, api_token). Raises if not configured."""
    account_id = get_value("cloudflare.account_id")
    api_token = get_value("cloudflare.api_token")
    if not account_id or not api_token:
        raise ConfigError(
            "Cloudflare credentials not configured.\n"
            "Run: crawldiff config set cloudflare.account_id <YOUR_ID>\n"
            "     crawldiff config set cloudflare.api_token <YOUR_TOKEN>\n"
            "Or set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN env vars."
        )
    return account_id, api_token


def mask_secret(value: str) -> str:
    """Mask a secret value for display, showing only last 4 chars."""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
