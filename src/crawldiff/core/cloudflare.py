"""Cloudflare /crawl API client.

Handles starting crawl jobs, polling for results, and parsing responses.
All Cloudflare API interactions are centralized here.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from rich.console import Console

err = Console(stderr=True)

BASE_URL = "https://api.cloudflare.com/client/v4/accounts"
POLL_INTERVAL = 3  # seconds between status checks
MAX_POLL_ATTEMPTS = 200  # ~10 minutes max wait


class CrawlStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CrawlPage:
    """A single crawled page result."""

    url: str
    markdown: str = ""
    html: str = ""
    status_code: int = 200


@dataclass
class CrawlResult:
    """Full result of a crawl job."""

    job_id: str
    status: CrawlStatus
    pages: list[CrawlPage] = field(default_factory=list)
    total_pages: int = 0


class CloudflareError(Exception):
    """Raised on Cloudflare API errors."""


def _build_headers(api_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }


def _crawl_url(account_id: str) -> str:
    return f"{BASE_URL}/{account_id}/browser-rendering/crawl"


async def start_crawl(
    account_id: str,
    api_token: str,
    url: str,
    *,
    depth: int = 2,
    max_pages: int = 50,
    formats: list[str] | None = None,
    modified_since: datetime | None = None,
    render: bool = True,
) -> str:
    """Start a crawl job. Returns the job ID."""
    if formats is None:
        formats = ["markdown"]

    body: dict[str, Any] = {
        "url": url,
        "formats": formats,
        "limit": max_pages,
        "depth": depth,
    }

    if not render:
        body["render"] = False

    if modified_since:
        # Cloudflare expects unix timestamp in seconds
        body["modifiedSince"] = int(modified_since.timestamp())

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _crawl_url(account_id),
            headers=_build_headers(api_token),
            json=body,
        )

    _handle_error(resp)
    data = resp.json()

    # Result is a plain string (the job ID) on success
    result = data.get("result", "")
    if isinstance(result, str) and result:
        return result
    # Fallback: result might be an object with "id"
    if isinstance(result, dict):
        job_id = result.get("id", "")
        if job_id:
            return job_id
    raise CloudflareError(f"No job ID in response: {data}")


async def get_crawl_result(
    account_id: str,
    api_token: str,
    job_id: str,
) -> CrawlResult:
    """Fetch the current state of a crawl job."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{_crawl_url(account_id)}/{job_id}",
            headers=_build_headers(api_token),
        )

    _handle_error(resp)
    data = resp.json()
    result = data.get("result", {})

    status_str = result.get("status", "pending")
    try:
        status = CrawlStatus(status_str)
    except ValueError:
        status = CrawlStatus.PENDING

    pages: list[CrawlPage] = []
    for record in result.get("records", []):
        # Skip non-completed records (e.g., "skipped")
        if record.get("status") != "completed":
            continue
        metadata = record.get("metadata", {})
        pages.append(CrawlPage(
            url=record.get("url", ""),
            markdown=record.get("markdown", ""),
            html=record.get("html", ""),
            status_code=metadata.get("status", 200),
        ))

    return CrawlResult(
        job_id=job_id,
        status=status,
        pages=pages,
        total_pages=result.get("total", len(pages)),
    )


async def wait_for_crawl(
    account_id: str,
    api_token: str,
    job_id: str,
    *,
    poll_interval: int = POLL_INTERVAL,
) -> CrawlResult:
    """Poll a crawl job until completion. Shows progress via rich spinner."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=err,
        transient=True,
    ) as progress:
        task = progress.add_task("Crawling...", total=None)

        for attempt in range(MAX_POLL_ATTEMPTS):
            result = await get_crawl_result(account_id, api_token, job_id)

            if result.status == CrawlStatus.COMPLETED:
                progress.update(
                    task,
                    description=f"Crawl complete — {len(result.pages)} pages",
                )
                return result

            if result.status == CrawlStatus.FAILED:
                raise CloudflareError(f"Crawl job {job_id} failed.")

            pages_so_far = len(result.pages)
            progress.update(
                task,
                description=(
                    f"Crawling... {pages_so_far} pages found"
                    f" (attempt {attempt + 1})"
                ),
            )

            await asyncio.sleep(poll_interval)

    timeout_secs = MAX_POLL_ATTEMPTS * poll_interval
    raise CloudflareError(
        f"Crawl job {job_id} timed out after {timeout_secs}s."
    )


def _handle_error(resp: httpx.Response) -> None:
    """Convert HTTP errors into user-friendly CloudflareError."""
    if resp.status_code == 200:
        return

    status = resp.status_code
    try:
        body = resp.json()
        errors = body.get("errors", [])
        msg = (
            "; ".join(e.get("message", "") for e in errors)
            if errors else resp.text
        )
    except Exception:
        msg = resp.text

    error_map: dict[int, str] = {
        401: "Invalid API token. Check your cloudflare.api_token config.",
        403: "Access denied. Your token may lack the required permissions.",
        429: "Rate limited by Cloudflare. Wait a moment and try again.",
    }

    prefix = error_map.get(status, f"Cloudflare API error ({status})")
    raise CloudflareError(f"{prefix}\n{msg}")
