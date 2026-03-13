"""Shared test fixtures."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from crawldiff.core.storage import get_db


@pytest.fixture
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test.db"
    conn = get_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def sample_pages() -> list[dict[str, str]]:
    """Sample crawl pages for testing."""
    return [
        {
            "url": "https://example.com/",
            "markdown": "# Welcome\n\nThis is the homepage.\n\n## Features\n\n- Fast\n- Simple\n",
            "html": "<h1>Welcome</h1><p>This is the homepage.</p>",
        },
        {
            "url": "https://example.com/pricing",
            "markdown": "# Pricing\n\n## Starter\n\n$25/month\n\n## Pro\n\n$99/month\n",
            "html": "<h1>Pricing</h1>",
        },
        {
            "url": "https://example.com/about",
            "markdown": "# About Us\n\nWe build tools for developers.\n",
            "html": "<h1>About Us</h1>",
        },
    ]


@pytest.fixture
def modified_pages() -> list[dict[str, str]]:
    """Modified version of sample pages — pricing changed, new page, about removed."""
    return [
        {
            "url": "https://example.com/",
            "markdown": "# Welcome\n\nThis is the homepage.\n\n## Features\n\n- Fast\n- Simple\n",
            "html": "<h1>Welcome</h1><p>This is the homepage.</p>",
        },
        {
            "url": "https://example.com/pricing",
            "markdown": (
                "# Pricing\n\n## Starter\n\n$30/month\n\n## Pro\n\n"
                "$99/month\n\n## Enterprise\n\nCustom pricing\n"
            ),
            "html": "<h1>Pricing</h1>",
        },
        {
            "url": "https://example.com/blog",
            "markdown": "# Blog\n\nOur latest posts.\n",
            "html": "<h1>Blog</h1>",
        },
    ]
