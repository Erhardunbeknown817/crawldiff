"""URL normalization utilities."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent storage and comparison.

    - Adds https:// if no scheme
    - Strips trailing slashes
    - Lowercases the hostname
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    # Lowercase hostname
    hostname = (parsed.hostname or "").lower()
    # Rebuild with normalized parts
    normalized = urlunparse((
        parsed.scheme,
        hostname + (f":{parsed.port}" if parsed.port else ""),
        parsed.path.rstrip("/") or "/",
        parsed.params,
        parsed.query,
        "",  # drop fragment
    ))
    return normalized


def get_domain(url: str) -> str:
    """Extract the domain from a URL."""
    parsed = urlparse(normalize_url(url))
    return parsed.hostname or url
