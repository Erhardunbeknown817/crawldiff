"""Tests for the diffing engine."""

from __future__ import annotations

import sqlite3

from crawldiff.core.differ import diff_snapshots
from crawldiff.core.storage import get_latest_snapshots, save_snapshot


def test_detect_added_page(tmp_db: sqlite3.Connection, sample_pages, modified_pages):
    """Blog page should appear as added."""
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-old")
    old = get_latest_snapshots(tmp_db, "https://example.com")

    save_snapshot(tmp_db, "https://example.com", modified_pages, "job-new")
    from crawldiff.core.storage import get_snapshots_by_job
    new = get_snapshots_by_job(tmp_db, "job-new")

    result = diff_snapshots(old, new)
    added_urls = [p.url for p in result.pages_added]
    assert "https://example.com/blog" in added_urls


def test_detect_removed_page(tmp_db: sqlite3.Connection, sample_pages, modified_pages):
    """About page should appear as removed."""
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-old")
    old = get_latest_snapshots(tmp_db, "https://example.com")

    save_snapshot(tmp_db, "https://example.com", modified_pages, "job-new")
    from crawldiff.core.storage import get_snapshots_by_job
    new = get_snapshots_by_job(tmp_db, "job-new")

    result = diff_snapshots(old, new)
    removed_urls = [p.url for p in result.pages_removed]
    assert "https://example.com/about" in removed_urls


def test_detect_modified_page(tmp_db: sqlite3.Connection, sample_pages, modified_pages):
    """Pricing page should appear as modified with diff."""
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-old")
    old = get_latest_snapshots(tmp_db, "https://example.com")

    save_snapshot(tmp_db, "https://example.com", modified_pages, "job-new")
    from crawldiff.core.storage import get_snapshots_by_job
    new = get_snapshots_by_job(tmp_db, "job-new")

    result = diff_snapshots(old, new)
    changed_urls = [p.url for p in result.pages_changed]
    assert "https://example.com/pricing" in changed_urls

    pricing_diff = next(p for p in result.pages_changed if "pricing" in p.url)
    assert "$25/month" in pricing_diff.unified_diff
    assert "$30/month" in pricing_diff.unified_diff


def test_unchanged_pages_counted(tmp_db: sqlite3.Connection, sample_pages, modified_pages):
    """Homepage should be counted as unchanged."""
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-old")
    old = get_latest_snapshots(tmp_db, "https://example.com")

    save_snapshot(tmp_db, "https://example.com", modified_pages, "job-new")
    from crawldiff.core.storage import get_snapshots_by_job
    new = get_snapshots_by_job(tmp_db, "job-new")

    result = diff_snapshots(old, new)
    assert result.pages_unchanged == 1  # homepage


def test_no_changes(tmp_db: sqlite3.Connection, sample_pages):
    """Same pages should produce no changes."""
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-old")
    old = get_latest_snapshots(tmp_db, "https://example.com")

    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-new")
    from crawldiff.core.storage import get_snapshots_by_job
    new = get_snapshots_by_job(tmp_db, "job-new")

    result = diff_snapshots(old, new)
    assert not result.has_changes
    assert result.pages_unchanged == 3


def test_ignore_whitespace(tmp_db: sqlite3.Connection):
    """Whitespace-only changes should be ignored when flag is set."""
    save_snapshot(tmp_db, "https://example.com", [
        {"url": "https://example.com/", "markdown": "# Hello\n\n  World  \n", "html": ""},
    ], "job-old")
    old = get_latest_snapshots(tmp_db, "https://example.com")

    save_snapshot(tmp_db, "https://example.com", [
        {"url": "https://example.com/", "markdown": "# Hello\n\nWorld\n", "html": ""},
    ], "job-new")
    from crawldiff.core.storage import get_snapshots_by_job
    new = get_snapshots_by_job(tmp_db, "job-new")

    result = diff_snapshots(old, new, ignore_whitespace=True)
    assert not result.has_changes
