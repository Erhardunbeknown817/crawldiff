"""Crawl command — snapshot a website."""

from __future__ import annotations

import asyncio
import time

import typer

from crawldiff.core import cloudflare
from crawldiff.core.storage import get_db, save_snapshot
from crawldiff.output.terminal import print_crawl_summary, print_error
from crawldiff.utils.config import ConfigError, get_cloudflare_credentials
from crawldiff.utils.url import normalize_url


def crawl(
    url: str = typer.Argument(help="URL to crawl"),
    depth: int = typer.Option(2, "--depth", "-d", help="Maximum crawl depth"),
    max_pages: int = typer.Option(50, "--max-pages", "-m", help="Maximum pages to crawl"),
    no_render: bool = typer.Option(False, "--no-render", help="Static mode (no browser rendering)"),
) -> None:
    """Crawl a website and store a snapshot locally."""
    try:
        account_id, api_token = get_cloudflare_credentials()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1) from None

    normalized = normalize_url(url)
    try:
        asyncio.run(_do_crawl(account_id, api_token, normalized, depth, max_pages, not no_render))
    except cloudflare.CloudflareError as e:
        print_error(str(e))
        raise typer.Exit(1) from None
    except Exception as e:  # noqa: BLE001
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1) from None


async def _do_crawl(
    account_id: str,
    api_token: str,
    url: str,
    depth: int,
    max_pages: int,
    render: bool,
) -> None:
    """Execute the crawl workflow."""
    start = time.time()

    # Start the crawl job
    job_id = await cloudflare.start_crawl(
        account_id,
        api_token,
        url,
        depth=depth,
        max_pages=max_pages,
        render=render,
    )

    # Wait for completion with progress spinner
    result = await cloudflare.wait_for_crawl(account_id, api_token, job_id)

    # Store in SQLite
    pages = [
        {
            "url": page.url,
            "markdown": page.markdown,
            "html": page.html,
        }
        for page in result.pages
    ]

    if pages:
        conn = get_db()
        try:
            save_snapshot(conn, url, pages, job_id)
        finally:
            conn.close()

    elapsed = time.time() - start
    print_crawl_summary(url, len(result.pages), elapsed)
