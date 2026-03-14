"""Watch command — continuously monitor a site for changes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import typer
from rich.console import Console

from crawldiff.core import cloudflare
from crawldiff.core.differ import diff_snapshots
from crawldiff.core.storage import get_db, get_latest_snapshots, get_snapshots_by_job, save_snapshot
from crawldiff.core.summarizer import summarize_diff
from crawldiff.output.terminal import print_diff_result, print_error
from crawldiff.utils.config import ConfigError, get_cloudflare_credentials, get_value
from crawldiff.utils.duration import parse_duration
from crawldiff.utils.url import normalize_url

err = Console(stderr=True)


def watch(
    url: str = typer.Argument(help="URL to watch for changes"),
    every: str = typer.Option("1h", "--every", "-e", help="Check interval (e.g., 30m, 1h, 6h)"),
    depth: int = typer.Option(2, "--depth", "-d", help="Maximum crawl depth"),
    max_pages: int = typer.Option(50, "--max-pages", "-m", help="Maximum pages per crawl"),
    no_summary: bool = typer.Option(False, "--no-summary", help="Skip AI summary"),
) -> None:
    """Watch a site and report changes on each interval."""
    try:
        account_id, api_token = get_cloudflare_credentials()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1) from None

    normalized = normalize_url(url)
    interval = int(parse_duration(every).total_seconds())

    err.print(f"[bold]Watching[/bold] {normalized} every {every}")
    err.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        asyncio.run(_watch_loop(
            account_id, api_token, normalized,
            interval=interval,
            depth=depth,
            max_pages=max_pages,
            no_summary=no_summary,
        ))
    except KeyboardInterrupt:
        err.print("\n[dim]Stopped watching.[/dim]")


async def _watch_loop(
    account_id: str,
    api_token: str,
    url: str,
    *,
    interval: int,
    depth: int,
    max_pages: int,
    no_summary: bool,
) -> None:
    """Main watch loop."""
    check_count = 0
    consecutive_failures = 0
    max_consecutive_failures = 5

    while True:
        check_count += 1
        now = datetime.now(UTC)
        err.print(f"[cyan]Check #{check_count}[/cyan] at {now.strftime('%H:%M:%S UTC')}")

        conn = get_db()
        try:
            old_pages = get_latest_snapshots(conn, url)

            # Crawl
            job_id = await cloudflare.start_crawl(
                account_id, api_token, url,
                depth=depth, max_pages=max_pages,
            )
            result = await cloudflare.wait_for_crawl(account_id, api_token, job_id)

            new_page_dicts = [
                {"url": p.url, "markdown": p.markdown, "html": p.html}
                for p in result.pages
            ]
            if new_page_dicts:
                save_snapshot(conn, url, new_page_dicts, job_id)

            if not old_pages:
                err.print(f"[green]Initial snapshot saved ({len(result.pages)} pages)[/green]")
            elif not new_page_dicts:
                err.print("[dim]No changes detected.[/dim]")
            else:
                new_pages = get_snapshots_by_job(conn, job_id)
                diff_result = diff_snapshots(old_pages, new_pages)

                if diff_result.has_changes:
                    ai_summary = ""
                    if not no_summary:
                        ai_provider = get_value("ai.provider")
                        if ai_provider and ai_provider != "none":
                            ai_summary = await summarize_diff(diff_result)

                    print_diff_result(diff_result, url, ai_summary=ai_summary)
                else:
                    err.print("[dim]No changes detected.[/dim]")

            consecutive_failures = 0

        except cloudflare.CloudflareError as e:
            consecutive_failures += 1
            print_error(str(e))
            if consecutive_failures >= max_consecutive_failures:
                print_error(
                    f"Stopping after {max_consecutive_failures} consecutive failures."
                )
                raise typer.Exit(1) from None
        finally:
            conn.close()

        # Wait for next interval
        err.print(f"[dim]Next check in {_format_seconds(interval)}...[/dim]\n")
        await asyncio.sleep(interval)



def _format_seconds(s: int) -> str:
    """Format seconds into a human-readable string."""
    if s >= 86400:
        return f"{s // 86400}d"
    if s >= 3600:
        return f"{s // 3600}h"
    if s >= 60:
        return f"{s // 60}m"
    return f"{s}s"
