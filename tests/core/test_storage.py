"""Tests for SQLite storage layer."""

from __future__ import annotations

import sqlite3

from crawldiff.core.storage import (
    content_hash,
    get_latest_snapshots,
    get_or_create_site,
    list_crawls,
    save_snapshot,
)


def test_content_hash_deterministic():
    assert content_hash("hello") == content_hash("hello")
    assert content_hash("hello") != content_hash("world")


def test_get_or_create_site(tmp_db: sqlite3.Connection):
    site_id = get_or_create_site(tmp_db, "https://example.com")
    assert site_id > 0

    # Same URL returns same ID
    same_id = get_or_create_site(tmp_db, "https://example.com")
    assert same_id == site_id

    # Different URL returns different ID
    other_id = get_or_create_site(tmp_db, "https://other.com")
    assert other_id != site_id


def test_save_and_retrieve_snapshot(tmp_db: sqlite3.Connection, sample_pages: list[dict[str, str]]):
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-001")

    snapshots = get_latest_snapshots(tmp_db, "https://example.com")
    assert len(snapshots) == 3

    urls = {s.url for s in snapshots}
    assert "https://example.com/" in urls
    assert "https://example.com/pricing" in urls


def test_latest_snapshots_returns_most_recent(tmp_db: sqlite3.Connection):
    # Save first version
    save_snapshot(tmp_db, "https://example.com", [
        {"url": "https://example.com/", "markdown": "# V1", "html": ""},
    ], "job-001")

    # Save second version
    save_snapshot(tmp_db, "https://example.com", [
        {"url": "https://example.com/", "markdown": "# V2", "html": ""},
    ], "job-002")

    snapshots = get_latest_snapshots(tmp_db, "https://example.com")
    assert len(snapshots) == 1
    assert snapshots[0].content_md == "# V2"


def test_list_crawls(tmp_db: sqlite3.Connection, sample_pages: list[dict[str, str]]):
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-001")
    save_snapshot(tmp_db, "https://example.com", sample_pages, "job-002")

    crawls = list_crawls(tmp_db, "https://example.com")
    assert len(crawls) == 2
    assert crawls[0].crawl_job_id in ("job-001", "job-002")


def test_no_snapshots_returns_empty(tmp_db: sqlite3.Connection):
    assert get_latest_snapshots(tmp_db, "https://nonexistent.com") == []
    assert list_crawls(tmp_db, "https://nonexistent.com") == []
