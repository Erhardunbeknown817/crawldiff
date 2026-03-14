"""Tests for the diff command."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.exceptions import Exit

from crawldiff.commands.diff import _do_diff
from crawldiff.core.cloudflare import CrawlPage, CrawlResult, CrawlStatus
from crawldiff.core.storage import get_db, save_snapshot

DIFF_START = "crawldiff.commands.diff.cloudflare.start_crawl"
DIFF_WAIT = "crawldiff.commands.diff.cloudflare.wait_for_crawl"
DIFF_DB = "crawldiff.commands.diff.get_db"
DIFF_PRINT = "crawldiff.commands.diff.print_diff_result"
DIFF_ERROR = "crawldiff.commands.diff.print_error"
DIFF_JSON = "crawldiff.commands.diff.print_diff_json"

DIFF_KWARGS = dict(
    since="7d", format="terminal", output_path=None,
    no_summary=True, depth=2, max_pages=50, ignore_whitespace=False,
)


@pytest.fixture
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    conn = get_db(tmp_path / "test.db")
    yield conn
    conn.close()


@pytest.fixture
def db_with_snapshot(tmp_db: sqlite3.Connection) -> sqlite3.Connection:
    """Database with an existing snapshot for diffing against."""
    pages = [
        {"url": "https://example.com/", "markdown": "# Home\nOriginal", "html": ""},
        {"url": "https://example.com/about", "markdown": "# About", "html": ""},
    ]
    save_snapshot(tmp_db, "https://example.com", pages, "old-job")
    return tmp_db


@pytest.mark.asyncio
async def test_diff_detects_changes(db_with_snapshot: sqlite3.Connection):
    """Diff should detect modified pages."""
    mock_result = CrawlResult(
        job_id="new-job", status=CrawlStatus.COMPLETED,
        pages=[CrawlPage(url="https://example.com/", markdown="# Home\nUpdated")],
        total_pages=1,
    )
    printed = {}

    def capture(diff_result, url, **kw):  # type: ignore[no-untyped-def]
        printed["result"] = diff_result

    with (
        patch(DIFF_START, new_callable=AsyncMock, return_value="new-job"),
        patch(DIFF_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(DIFF_DB, return_value=db_with_snapshot),
        patch(DIFF_PRINT, side_effect=capture),
    ):
        await _do_diff("acc", "tok", "https://example.com", **DIFF_KWARGS)

    assert printed["result"].has_changes
    assert len(printed["result"].pages_changed) == 1


@pytest.mark.asyncio
async def test_diff_no_previous_snapshot(tmp_db: sqlite3.Connection):
    """Diff with no existing snapshot should exit with error."""
    with (
        patch(DIFF_DB, return_value=tmp_db),
        patch(DIFF_ERROR) as mock_error,
        pytest.raises(Exit),
    ):
        await _do_diff("acc", "tok", "https://example.com", **DIFF_KWARGS)

    mock_error.assert_called_once()
    assert "No previous snapshot" in mock_error.call_args[0][0]


@pytest.mark.asyncio
async def test_diff_no_changes(db_with_snapshot: sqlite3.Connection):
    """Diff with identical content should report no changes."""
    mock_result = CrawlResult(
        job_id="new-job", status=CrawlStatus.COMPLETED,
        pages=[], total_pages=0,
    )
    printed = {}

    def capture(diff_result, url, **kw):  # type: ignore[no-untyped-def]
        printed["result"] = diff_result

    with (
        patch(DIFF_START, new_callable=AsyncMock, return_value="new-job"),
        patch(DIFF_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(DIFF_DB, return_value=db_with_snapshot),
        patch(DIFF_PRINT, side_effect=capture),
    ):
        await _do_diff("acc", "tok", "https://example.com", **DIFF_KWARGS)

    assert not printed["result"].has_changes


@pytest.mark.asyncio
async def test_diff_json_output(db_with_snapshot: sqlite3.Connection):
    """Diff with --format json should call print_diff_json."""
    mock_result = CrawlResult(
        job_id="new-job", status=CrawlStatus.COMPLETED,
        pages=[], total_pages=0,
    )

    with (
        patch(DIFF_START, new_callable=AsyncMock, return_value="new-job"),
        patch(DIFF_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(DIFF_DB, return_value=db_with_snapshot),
        patch(DIFF_JSON) as mock_json,
    ):
        await _do_diff(
            "acc", "tok", "https://example.com",
            **{**DIFF_KWARGS, "format": "json"},
        )

    mock_json.assert_called_once()


@pytest.mark.asyncio
async def test_diff_markdown_to_file(
    db_with_snapshot: sqlite3.Connection, tmp_path: Path,
):
    """Diff with --format markdown --output should write to file."""
    mock_result = CrawlResult(
        job_id="new-job", status=CrawlStatus.COMPLETED,
        pages=[], total_pages=0,
    )
    output_file = tmp_path / "report.md"

    with (
        patch(DIFF_START, new_callable=AsyncMock, return_value="new-job"),
        patch(DIFF_WAIT, new_callable=AsyncMock, return_value=mock_result),
        patch(DIFF_DB, return_value=db_with_snapshot),
    ):
        await _do_diff(
            "acc", "tok", "https://example.com",
            **{**DIFF_KWARGS, "format": "markdown", "output_path": str(output_file)},
        )

    assert output_file.exists()
    assert "crawldiff report" in output_file.read_text()
