"""History command — view past crawl snapshots."""

from __future__ import annotations

import typer

from crawldiff.core.storage import get_db, list_crawls
from crawldiff.output.terminal import print_history_table
from crawldiff.utils.url import normalize_url


def history(
    url: str = typer.Argument(help="URL to show history for"),
) -> None:
    """List all crawl snapshots for a site."""
    normalized = normalize_url(url)
    conn = get_db()
    try:
        crawls = list_crawls(conn, normalized)
        rows = [
            {
                "job_id": c.crawl_job_id,
                "crawled_at": c.crawled_at,
                "page_count": c.page_count,
            }
            for c in crawls
        ]
        print_history_table(rows, normalized)
    finally:
        conn.close()
