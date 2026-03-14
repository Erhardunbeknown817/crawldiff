"""URL normalization utilities."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent storage and comparison.

    - Adds https:// if no scheme
    - Strips trailing slashes
    - Lowercases the hostname
    """
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    # Lowercase hostname
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError(f"Invalid URL: no hostname found in '{url}'")
    # Handle invalid port numbers gracefully
    try:
        port_part = f":{parsed.port}" if parsed.port else ""
    except ValueError:
        port_part = ""
    # Rebuild with normalized parts
    normalized = urlunparse((
        parsed.scheme,
        hostname + port_part,
        parsed.path.rstrip("/") or "/",
        parsed.params,
        parsed.query,
        "",  # drop fragment
    ))
    return normalized
