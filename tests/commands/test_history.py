"""Tests for the history command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from crawldiff.commands.history import history
from crawldiff.core.storage import get_db, save_snapshot
from crawldiff.utils.url import normalize_url


def test_history_with_crawls(tmp_path: Path):
    """History should display past crawls."""
    conn = get_db(tmp_path / "test.db")
    url = normalize_url("https://example.com")
    pages = [{"url": "https://example.com/", "markdown": "# Home", "html": ""}]
    save_snapshot(conn, url, pages, "job-111")
    save_snapshot(conn, url, pages, "job-222")

    printed = {}

    def capture_table(rows, url):  # type: ignore[no-untyped-def]
        printed["rows"] = rows
        printed["url"] = url

    with (
        patch("crawldiff.commands.history.get_db", return_value=conn),
        patch("crawldiff.commands.history.print_history_table", side_effect=capture_table),
    ):
        history("https://example.com")

    conn.close()
    assert len(printed["rows"]) == 2
    job_ids = {r["job_id"] for r in printed["rows"]}
    assert "job-111" in job_ids
    assert "job-222" in job_ids


def test_history_no_crawls(tmp_path: Path):
    """History for unknown site should show empty table."""
    conn = get_db(tmp_path / "test.db")

    printed = {}

    def capture_table(rows, url):  # type: ignore[no-untyped-def]
        printed["rows"] = rows

    with (
        patch("crawldiff.commands.history.get_db", return_value=conn),
        patch("crawldiff.commands.history.print_history_table", side_effect=capture_table),
    ):
        history("https://unknown.com")

    conn.close()
    assert printed["rows"] == []
