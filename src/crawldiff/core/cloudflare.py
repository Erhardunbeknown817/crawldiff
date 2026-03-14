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
MAX_RETRIES = 3  # retry on transient errors
RETRY_BASE_DELAY = 5  # seconds, doubles on each retry


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

    resp = await _request_with_retry(
        "POST", _crawl_url(account_id), api_token, json=body,
    )
    data = resp.json()

    # Result is a plain string (the job ID) on success
    result = data.get("result", "")
    if isinstance(result, str) and result:
        return result
    # Fallback: result might be an object with "id"
    if isinstance(result, dict):
        job_id = result.get("id", "")
        if isinstance(job_id, str) and job_id:
            return job_id
    raise CloudflareError(f"No job ID in response: {data}")


async def get_crawl_result(
    account_id: str,
    api_token: str,
    job_id: str,
) -> CrawlResult:
    """Fetch the current state of a crawl job."""
    resp = await _request_with_retry(
        "GET", f"{_crawl_url(account_id)}/{job_id}", api_token,
    )
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


async def _request_with_retry(
    method: str,
    url: str,
    api_token: str,
    **kwargs: Any,
) -> httpx.Response:
    """Make an HTTP request with retry on rate limits and transient errors."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method, url, headers=_build_headers(api_token), **kwargs,
                )
            _handle_error(resp)
            return resp
        except _RateLimitError as e:
            if attempt >= MAX_RETRIES:
                raise CloudflareError(
                    "Rate limited by Cloudflare after retries. Try again later."
                ) from e
            delay = e.retry_after or (RETRY_BASE_DELAY * (2 ** attempt))
            err.print(f"[yellow]Rate limited, retrying in {delay}s...[/yellow]")
            await asyncio.sleep(delay)
        except httpx.TimeoutException as e:
            if attempt >= MAX_RETRIES:
                raise CloudflareError(
                    "Request timed out after retries. Check your network."
                ) from e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            err.print(f"[yellow]Timeout, retrying in {delay}s...[/yellow]")
            await asyncio.sleep(delay)
    raise CloudflareError("Request failed after retries.")  # unreachable but satisfies mypy


class _RateLimitError(CloudflareError):
    """Raised on 429 responses to trigger retry logic."""

    def __init__(self, retry_after: int = 0) -> None:
        self.retry_after = retry_after
        super().__init__("Rate limited by Cloudflare.")


def _handle_error(resp: httpx.Response) -> None:
    """Convert HTTP errors into user-friendly CloudflareError."""
    if resp.status_code == 200:
        return

    status = resp.status_code

    # Raise retryable error for rate limits
    if status == 429:
        retry_after = int(resp.headers.get("Retry-After", "0"))
        raise _RateLimitError(retry_after)

    try:
        body = resp.json()
        errors = body.get("errors", [])
        msg = (
            "; ".join(e.get("message", "") for e in errors)
            if errors else resp.text
        )
    except (ValueError, KeyError):
        msg = resp.text

    error_map: dict[int, str] = {
        401: "Invalid API token. Check your cloudflare.api_token config.",
        403: "Access denied. Your token may lack the required permissions.",
    }

    prefix = error_map.get(status, f"Cloudflare API error ({status})")
    raise CloudflareError(f"{prefix}\n{msg}")
