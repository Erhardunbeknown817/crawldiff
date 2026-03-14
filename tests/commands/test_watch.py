"""Tests for the watch command."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.exceptions import Exit

from crawldiff.commands.watch import _format_seconds, _watch_loop
from crawldiff.core.cloudflare import CloudflareError, CrawlPage, CrawlResult, CrawlStatus
from crawldiff.core.storage import get_db, save_snapshot

WATCH_START = "crawldiff.commands.watch.cloudflare.start_crawl"
WATCH_WAIT = "crawldiff.commands.watch.cloudflare.wait_for_crawl"
WATCH_DB = "crawldiff.commands.watch.get_db"
WATCH_PRINT = "crawldiff.commands.watch.print_diff_result"
WATCH_ERROR = "crawldiff.commands.watch.print_error"


@pytest.fixture
def db_with_snapshot(tmp_db: sqlite3.Connection) -> sqlite3.Connection:
    pages = [
        {"url": "https://example.com/", "markdown": "# Home\nOriginal", "html": ""},
    ]
    save_snapshot(tmp_db, "https://example.com", pages, "old-job")
    return tmp_db


def _one_iteration() -> tuple[list[bool], object]:
    """Return a shutdown flag that stops after one iteration."""
    calls: list[bool] = []

    def flag() -> bool:
        calls.append(True)
        return len(calls) > 1

    return calls, flag


@pytest.mark.asyncio
async def test_watch_initial_snapshot(tmp_db: sqlite3.Connection) -> None:
    """First watch iteration should save initial snapshot."""
    _, shutdown = _one_iteration()
    mock_result = CrawlResult(
        job_id="job-1", status=CrawlStatus.COMPLETED,
        pages=[CrawlPage(url="https://example.com/", markdown="# Home")],
        total_pages=1,
    )

    with (
        patch(WATCH_START, new_callable=AsyncMock, return_value="job-1"),
        patch(WATCH_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(WATCH_DB, return_value=tmp_db),
    ):
        await _watch_loop(
            "acc", "tok", "https://example.com",
            interval=0, depth=2, max_pages=50, no_summary=True,
            shutdown_flag=shutdown,
        )


@pytest.mark.asyncio
async def test_watch_detects_changes(db_with_snapshot: sqlite3.Connection) -> None:
    """Watch should detect and print changes."""
    _, shutdown = _one_iteration()
    mock_result = CrawlResult(
        job_id="job-2", status=CrawlStatus.COMPLETED,
        pages=[CrawlPage(url="https://example.com/", markdown="# Home\nUpdated")],
        total_pages=1,
    )
    printed = {}

    def capture(diff_result, url, **kw):  # type: ignore[no-untyped-def]
        printed["result"] = diff_result

    with (
        patch(WATCH_START, new_callable=AsyncMock, return_value="job-2"),
        patch(WATCH_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(WATCH_DB, return_value=db_with_snapshot),
        patch(WATCH_PRINT, side_effect=capture),
    ):
        await _watch_loop(
            "acc", "tok", "https://example.com",
            interval=0, depth=2, max_pages=50, no_summary=True,
            shutdown_flag=shutdown,
        )

    assert printed["result"].has_changes


@pytest.mark.asyncio
async def test_watch_no_changes(db_with_snapshot: sqlite3.Connection) -> None:
    """Watch with no changed pages should not print diff."""
    _, shutdown = _one_iteration()
    mock_result = CrawlResult(
        job_id="job-3", status=CrawlStatus.COMPLETED,
        pages=[], total_pages=0,
    )

    with (
        patch(WATCH_START, new_callable=AsyncMock, return_value="job-3"),
        patch(WATCH_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(WATCH_DB, return_value=db_with_snapshot),
        patch(WATCH_PRINT) as mock_print,
    ):
        await _watch_loop(
            "acc", "tok", "https://example.com",
            interval=0, depth=2, max_pages=50, no_summary=True,
            shutdown_flag=shutdown,
        )

    mock_print.assert_not_called()


@pytest.mark.asyncio
async def test_watch_consecutive_failures_exit(tmp_path: Path) -> None:
    """Watch should exit after max consecutive failures."""
    with (
        patch(WATCH_START, new_callable=AsyncMock, side_effect=CloudflareError("fail")),
        patch(WATCH_DB, side_effect=lambda: get_db(tmp_path / "test.db")),
        patch(WATCH_ERROR),
        pytest.raises(Exit),
    ):
        await _watch_loop(
            "acc", "tok", "https://example.com",
            interval=0, depth=2, max_pages=50, no_summary=True,
        )


@pytest.mark.asyncio
async def test_watch_recovers_after_failure(tmp_path: Path) -> None:
    """A success after failures should reset the failure counter."""
    iteration = 0

    def fresh_db() -> sqlite3.Connection:
        """Return a fresh connection each call (watch closes conn each iteration)."""
        conn = get_db(tmp_path / "test.db")
        if iteration == 0:
            save_snapshot(conn, "https://example.com", [
                {"url": "https://example.com/", "markdown": "# Home", "html": ""},
            ], "old-job")
        return conn

    async def start_crawl_side(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal iteration
        iteration += 1
        if iteration <= 2:
            raise CloudflareError("transient")
        return "job-ok"

    mock_result = CrawlResult(
        job_id="job-ok", status=CrawlStatus.COMPLETED,
        pages=[], total_pages=0,
    )

    def shutdown() -> bool:
        return iteration >= 3

    with (
        patch(WATCH_START, new_callable=AsyncMock, side_effect=start_crawl_side),
        patch(WATCH_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(WATCH_DB, side_effect=fresh_db),
        patch(WATCH_ERROR) as mock_err,
        patch(WATCH_PRINT),
    ):
        # 2 failures then success — should not exit (max is 5)
        await _watch_loop(
            "acc", "tok", "https://example.com",
            interval=0, depth=2, max_pages=50, no_summary=True,
            shutdown_flag=shutdown,
        )

    assert mock_err.call_count >= 2


@pytest.mark.asyncio
async def test_watch_shutdown_flag_stops_loop(tmp_db: sqlite3.Connection) -> None:
    """Shutdown flag should stop the loop gracefully."""
    _, shutdown = _one_iteration()
    mock_result = CrawlResult(
        job_id="job-1", status=CrawlStatus.COMPLETED,
        pages=[CrawlPage(url="https://example.com/", markdown="# Home")],
        total_pages=1,
    )

    with (
        patch(WATCH_START, new_callable=AsyncMock, return_value="job-1"),
        patch(WATCH_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(WATCH_DB, return_value=tmp_db),
    ):
        # Should return without hanging
        await _watch_loop(
            "acc", "tok", "https://example.com",
            interval=0, depth=2, max_pages=50, no_summary=True,
            shutdown_flag=shutdown,
        )


def test_format_seconds() -> None:
    """Test human-readable time formatting."""
    assert _format_seconds(30) == "30s"
    assert _format_seconds(60) == "1m"
    assert _format_seconds(3600) == "1h"
    assert _format_seconds(86400) == "1d"
    assert _format_seconds(7200) == "2h"
