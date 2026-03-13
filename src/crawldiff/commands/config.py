"""Config management commands."""

from __future__ import annotations

import typer

from crawldiff.output.terminal import print_config_table, print_error, print_success
from crawldiff.utils.config import get_value, load_config, mask_secret, set_value

config_app = typer.Typer(help="Manage crawldiff configuration.")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Config key (e.g., cloudflare.account_id)"),
    value: str = typer.Argument(help="Config value"),
) -> None:
    """Set a configuration value."""
    valid_keys = {
        "cloudflare.account_id",
        "cloudflare.api_token",
        "ai.provider",
        "ai.model",
        "ai.api_key",
        "defaults.format",
        "defaults.depth",
        "defaults.max_pages",
    }

    if key not in valid_keys:
        print_error(f"Unknown config key: {key}\nValid keys: {', '.join(sorted(valid_keys))}")
        raise typer.Exit(1)

    set_value(key, value)
    display_val = mask_secret(value) if "token" in key or "key" in key else value
    print_success(f"{key} = {display_val}")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(help="Config key to read"),
) -> None:
    """Get a configuration value."""
    value = get_value(key)
    if not value:
        print_error(f"No value set for {key}")
        raise typer.Exit(1)

    display_val = mask_secret(value) if "token" in key or "key" in key else value
    typer.echo(display_val)


@config_app.command("show")
def config_show() -> None:
    """Show all configuration (secrets masked)."""
    config = load_config()
    flat: dict[str, str] = {}
    _flatten(config, "", flat)

    # Mask secrets
    for key in flat:
        if "token" in key or "key" in key:
            flat[key] = mask_secret(flat[key]) if flat[key] else "(not set)"
        elif not flat[key]:
            flat[key] = "(not set)"

    print_config_table(flat)


def _flatten(d: dict[str, object], prefix: str, result: dict[str, str]) -> None:
    """Flatten nested dict to dot-notation keys."""
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            _flatten(v, full_key, result)
        else:
            result[full_key] = str(v)
