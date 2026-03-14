"""Duration parsing utilities."""

from __future__ import annotations

import re
from datetime import timedelta

import typer


def parse_duration(s: str) -> timedelta:
    """Parse a human-friendly duration string into a timedelta.

    Supports: 30m, 1h, 6h, 1d, 7d, 2w, 30d, etc.
    """
    match = re.match(r"^(\d+)\s*([mhdw])$", s.strip().lower())
    if not match:
        raise typer.BadParameter(
            f"Invalid duration: '{s}'. Use format like 30m, 1h, 7d, 2w"
        )

    amount = int(match.group(1))
    unit = match.group(2)

    if amount == 0:
        raise typer.BadParameter(
            f"Invalid duration: '{s}'. Value must be greater than zero."
        )

    multipliers = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
    return timedelta(seconds=amount * multipliers[unit])
