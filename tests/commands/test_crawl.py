"""Tests for the crawl command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from crawldiff.commands.crawl import _do_crawl
from crawldiff.core.cloudflare import CrawlPage, CrawlResult, CrawlStatus
from crawldiff.core.storage import get_db

CRAWL_START = "crawldiff.commands.crawl.cloudflare.start_crawl"
CRAWL_WAIT = "crawldiff.commands.crawl.cloudflare.wait_for_crawl"
CRAWL_DB = "crawldiff.commands.crawl.get_db"
CRAWL_SUMMARY = "crawldiff.commands.crawl.print_crawl_summary"


@pytest.mark.asyncio
async def test_do_crawl_saves_snapshots(tmp_path: Path):
    """Crawl workflow should save pages to the database."""
    db_path = tmp_path / "test.db"
    mock_result = CrawlResult(
        job_id="job-123",
        status=CrawlStatus.COMPLETED,
        pages=[
            CrawlPage(url="https://example.com/", markdown="# Home"),
            CrawlPage(url="https://example.com/about", markdown="# About"),
        ],
        total_pages=2,
    )

    with (
        patch(CRAWL_START, new_callable=AsyncMock, return_value="job-123"),
        patch(CRAWL_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(CRAWL_DB, side_effect=lambda: get_db(db_path)),
        patch(CRAWL_SUMMARY),
    ):
        await _do_crawl("acc", "tok", "https://example.com", 2, 50, True)

    conn = get_db(db_path)
    rows = conn.execute("SELECT url FROM snapshots").fetchall()
    urls = {r["url"] for r in rows}
    conn.close()
    assert "https://example.com/" in urls
    assert "https://example.com/about" in urls


@pytest.mark.asyncio
async def test_do_crawl_empty_result(tmp_path: Path):
    """Crawl with zero pages should not crash."""
    db_path = tmp_path / "test.db"
    mock_result = CrawlResult(
        job_id="job-empty",
        status=CrawlStatus.COMPLETED,
        pages=[],
        total_pages=0,
    )

    with (
        patch(CRAWL_START, new_callable=AsyncMock, return_value="job-empty"),
        patch(CRAWL_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(CRAWL_DB, side_effect=lambda: get_db(db_path)),
        patch(CRAWL_SUMMARY),
    ):
        await _do_crawl("acc", "tok", "https://example.com", 2, 50, True)

    conn = get_db(db_path)
    rows = conn.execute("SELECT COUNT(*) as cnt FROM snapshots").fetchone()
    conn.close()
    assert rows["cnt"] == 0
