"""SQLite snapshot storage.

All database interactions are centralized here.
DB is stored at ~/.crawldiff/snapshots.db.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from crawldiff.utils.config import DB_PATH, ensure_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    url TEXT NOT NULL,
    content_md TEXT,
    content_html TEXT,
    content_hash TEXT NOT NULL,
    crawl_job_id TEXT,
    crawled_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS diffs (
    id INTEGER PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    crawl_old_job TEXT,
    crawl_new_job TEXT,
    pages_added INTEGER DEFAULT 0,
    pages_removed INTEGER DEFAULT 0,
    pages_changed INTEGER DEFAULT 0,
    ai_summary TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_snapshots_site_url
    ON snapshots(site_id, url, crawled_at);

CREATE INDEX IF NOT EXISTS idx_snapshots_job
    ON snapshots(crawl_job_id);
"""


@dataclass
class PageSnapshot:
    """A stored snapshot of a single page."""

    id: int
    site_id: int
    url: str
    content_md: str
    content_html: str
    content_hash: str
    crawl_job_id: str
    crawled_at: str


@dataclass
class CrawlRecord:
    """Summary of a stored crawl."""

    crawl_job_id: str
    crawled_at: str
    page_count: int


def content_hash(text: str) -> str:
    """SHA-256 hash of content for quick change detection."""
    return hashlib.sha256(text.encode()).hexdigest()


def get_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Open (and initialize) the database."""
    path = db_path or DB_PATH
    ensure_dir()
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def get_or_create_site(conn: sqlite3.Connection, url: str) -> int:
    """Get site ID, creating the record if needed."""
    row = conn.execute("SELECT id FROM sites WHERE url = ?", (url,)).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute("INSERT INTO sites (url) VALUES (?)", (url,))
    conn.commit()
    if cursor.lastrowid is None:
        msg = "Database insert failed: no row ID returned"
        raise RuntimeError(msg)
    return cursor.lastrowid


def save_snapshot(
    conn: sqlite3.Connection,
    site_url: str,
    pages: list[dict[str, str]],
    crawl_job_id: str,
) -> int:
    """Save a crawl's pages as snapshots. Returns site_id."""
    site_id = get_or_create_site(conn, site_url)

    for page in pages:
        md = page.get("markdown", "")
        html = page.get("html", "")
        page_hash = content_hash(md or html)
        conn.execute(
            """INSERT INTO snapshots
               (site_id, url, content_md, content_html, content_hash, crawl_job_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (site_id, page["url"], md, html, page_hash, crawl_job_id),
        )

    conn.commit()
    return site_id


def get_latest_snapshots(conn: sqlite3.Connection, site_url: str) -> list[PageSnapshot]:
    """Get the most recent snapshot for each page of a site."""
    site_id_row = conn.execute("SELECT id FROM sites WHERE url = ?", (site_url,)).fetchone()
    if not site_id_row:
        return []

    site_id = site_id_row["id"]
    rows = conn.execute(
        """SELECT s.* FROM snapshots s
           INNER JOIN (
               SELECT url, MAX(id) as max_id
               FROM snapshots WHERE site_id = ?
               GROUP BY url
           ) latest ON s.id = latest.max_id
           WHERE s.site_id = ?""",
        (site_id, site_id),
    ).fetchall()

    return [PageSnapshot(**dict(r)) for r in rows]


def get_snapshots_by_job(conn: sqlite3.Connection, crawl_job_id: str) -> list[PageSnapshot]:
    """Get all snapshots from a specific crawl job."""
    rows = conn.execute(
        "SELECT * FROM snapshots WHERE crawl_job_id = ?",
        (crawl_job_id,),
    ).fetchall()
    return [PageSnapshot(**dict(r)) for r in rows]


def list_crawls(conn: sqlite3.Connection, site_url: str) -> list[CrawlRecord]:
    """List all crawl jobs for a site."""
    site_id_row = conn.execute("SELECT id FROM sites WHERE url = ?", (site_url,)).fetchone()
    if not site_id_row:
        return []

    site_id = site_id_row["id"]
    rows = conn.execute(
        """SELECT crawl_job_id, MAX(crawled_at) as crawled_at, COUNT(*) as page_count
           FROM snapshots WHERE site_id = ?
           GROUP BY crawl_job_id
           ORDER BY crawled_at DESC""",
        (site_id,),
    ).fetchall()

    return [CrawlRecord(
        crawl_job_id=r["crawl_job_id"],
        crawled_at=r["crawled_at"],
        page_count=r["page_count"],
    ) for r in rows]


