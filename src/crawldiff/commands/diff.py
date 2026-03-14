"""Diff command — show what changed on a website."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

import typer

from crawldiff.core import cloudflare
from crawldiff.core.differ import diff_snapshots
from crawldiff.core.storage import get_db, get_latest_snapshots, get_snapshots_by_job, save_snapshot
from crawldiff.core.summarizer import summarize_diff
from crawldiff.output.json_out import print_diff_json
from crawldiff.output.markdown import render_diff_markdown
from crawldiff.output.terminal import print_diff_result, print_error
from crawldiff.utils.config import ConfigError, get_cloudflare_credentials, get_value
from crawldiff.utils.duration import parse_duration
from crawldiff.utils.url import normalize_url


def diff(
    url: str = typer.Argument(help="URL to diff"),
    since: str = typer.Option("7d", "--since", "-s", help="Time period (e.g., 1h, 7d, 2w, 30d)"),
    format: str = typer.Option(
        "terminal", "--format", "-f", help="Output format: terminal, json, markdown",
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Write report to file"),
    no_summary: bool = typer.Option(False, "--no-summary", help="Skip AI summary"),
    depth: int = typer.Option(2, "--depth", "-d", help="Maximum crawl depth"),
    max_pages: int = typer.Option(50, "--max-pages", "-m", help="Maximum pages to crawl"),
    ignore_whitespace: bool = typer.Option(
        False, "--ignore-whitespace", "-w", help="Ignore whitespace changes",
    ),
) -> None:
    """Show what changed on a website since the last crawl."""
    try:
        account_id, api_token = get_cloudflare_credentials()
    except ConfigError as e:
        print_error(str(e))
        raise typer.Exit(1) from None

    normalized = normalize_url(url)
    try:
        asyncio.run(_do_diff(
            account_id, api_token, normalized,
            since=since,
            format=format,
            output_path=output,
            no_summary=no_summary,
            depth=depth,
            max_pages=max_pages,
            ignore_whitespace=ignore_whitespace,
        ))
    except cloudflare.CloudflareError as e:
        print_error(str(e))
        raise typer.Exit(1) from None
    except Exception as e:  # noqa: BLE001
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1) from None


async def _do_diff(
    account_id: str,
    api_token: str,
    url: str,
    *,
    since: str,
    format: str,
    output_path: str | None,
    no_summary: bool,
    depth: int,
    max_pages: int,
    ignore_whitespace: bool,
) -> None:
    """Execute the diff workflow."""
    conn = get_db()
    try:
        # Get old snapshots
        old_pages = get_latest_snapshots(conn, url)

        if not old_pages:
            print_error(
                f"No previous snapshot for {url}\n"
                f"Run first: crawldiff crawl {url}"
            )
            raise typer.Exit(1) from None

        # Parse the 'since' duration to get modifiedSince
        since_delta = parse_duration(since)
        modified_since = datetime.now(UTC) - since_delta

        # Crawl with modifiedSince for efficiency
        job_id = await cloudflare.start_crawl(
            account_id,
            api_token,
            url,
            depth=depth,
            max_pages=max_pages,
            modified_since=modified_since,
        )

        result = await cloudflare.wait_for_crawl(account_id, api_token, job_id)

        # Save new snapshots (only the changed pages returned by API)
        new_page_dicts = [
            {"url": p.url, "markdown": p.markdown, "html": p.html}
            for p in result.pages
        ]
        if new_page_dicts:
            save_snapshot(conn, url, new_page_dicts, job_id)

        # Build the full new page set for diffing:
        # modifiedSince only returns changed pages, so we merge
        # the new results with old pages that weren't re-crawled
        changed_pages = get_snapshots_by_job(conn, job_id) if new_page_dicts else []
        changed_urls = {p.url for p in changed_pages}

        # Carry forward unchanged old pages + overlay changed pages
        new_pages = [p for p in old_pages if p.url not in changed_urls]
        new_pages.extend(changed_pages)

        # Diff
        diff_result = diff_snapshots(
            old_pages, new_pages, ignore_whitespace=ignore_whitespace
        )

        # AI summary
        ai_summary = ""
        if not no_summary and diff_result.has_changes:
            ai_provider = get_value("ai.provider")
            if ai_provider and ai_provider != "none":
                ai_summary = await summarize_diff(diff_result)

        # Output
        if format == "json":
            print_diff_json(diff_result, url, ai_summary)
        elif format == "markdown":
            md = render_diff_markdown(diff_result, url, ai_summary)
            if output_path:
                _write_output(output_path, md)
            else:
                sys.stdout.write(md)
        else:  # terminal
            print_diff_result(diff_result, url, since=since, ai_summary=ai_summary)
            if output_path:
                md = render_diff_markdown(diff_result, url, ai_summary)
                _write_output(output_path, md)

    finally:
        conn.close()


def _write_output(path: str, content: str) -> None:
    """Write output to a file with error handling."""
    try:
        Path(path).write_text(content)
    except OSError as e:
        print_error(f"Failed to write output file: {e}")
        raise typer.Exit(1) from None
