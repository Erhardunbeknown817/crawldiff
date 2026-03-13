"""Tests for the Cloudflare /crawl API client."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from crawldiff.core.cloudflare import (
    CloudflareError,
    CrawlStatus,
    get_crawl_result,
    start_crawl,
)

ACCOUNT_ID = "test-account-123"
API_TOKEN = "test-token-456"
BASE = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/browser-rendering/crawl"


@pytest.mark.asyncio
@respx.mock
async def test_start_crawl_returns_job_id():
    respx.post(BASE).mock(return_value=httpx.Response(
        200,
        json={"success": True, "result": "job-abc-123"},
    ))

    job_id = await start_crawl(ACCOUNT_ID, API_TOKEN, "https://example.com")
    assert job_id == "job-abc-123"


@pytest.mark.asyncio
@respx.mock
async def test_start_crawl_sends_correct_body():
    route = respx.post(BASE).mock(return_value=httpx.Response(
        200,
        json={"success": True, "result": "job-123"},
    ))

    await start_crawl(
        ACCOUNT_ID, API_TOKEN, "https://example.com",
        depth=3, max_pages=100,
    )

    request = route.calls[0].request
    import json
    body = json.loads(request.content)
    assert body["url"] == "https://example.com"
    assert body["depth"] == 3
    assert body["limit"] == 100
    assert body["formats"] == ["markdown"]


@pytest.mark.asyncio
@respx.mock
async def test_start_crawl_with_modified_since():
    route = respx.post(BASE).mock(return_value=httpx.Response(
        200,
        json={"success": True, "result": "job-123"},
    ))

    since = datetime(2026, 3, 10, 0, 0, 0, tzinfo=UTC)
    await start_crawl(
        ACCOUNT_ID, API_TOKEN, "https://example.com",
        modified_since=since,
    )

    import json
    body = json.loads(route.calls[0].request.content)
    assert "modifiedSince" in body
    assert isinstance(body["modifiedSince"], int)


@pytest.mark.asyncio
@respx.mock
async def test_start_crawl_auth_error():
    respx.post(BASE).mock(return_value=httpx.Response(
        401,
        json={"errors": [{"message": "Invalid token"}]},
    ))

    with pytest.raises(CloudflareError, match="Invalid API token"):
        await start_crawl(ACCOUNT_ID, API_TOKEN, "https://example.com")


@pytest.mark.asyncio
@respx.mock
async def test_get_crawl_result_complete():
    respx.get(f"{BASE}/job-123").mock(return_value=httpx.Response(
        200,
        json={
            "success": True,
            "result": {
                "id": "job-123",
                "status": "completed",
                "total": 2,
                "finished": 2,
                "records": [
                    {
                        "url": "https://example.com/",
                        "status": "completed",
                        "metadata": {"status": 200, "title": "Home"},
                        "markdown": "# Home",
                    },
                    {
                        "url": "https://example.com/about",
                        "status": "completed",
                        "metadata": {"status": 200, "title": "About"},
                        "markdown": "# About",
                    },
                ],
            },
        },
    ))

    result = await get_crawl_result(ACCOUNT_ID, API_TOKEN, "job-123")
    assert result.status == CrawlStatus.COMPLETED
    assert len(result.pages) == 2
    assert result.pages[0].url == "https://example.com/"
    assert result.pages[0].markdown == "# Home"


@pytest.mark.asyncio
@respx.mock
async def test_get_crawl_result_skips_non_completed():
    respx.get(f"{BASE}/job-123").mock(return_value=httpx.Response(
        200,
        json={
            "success": True,
            "result": {
                "id": "job-123",
                "status": "completed",
                "total": 2,
                "records": [
                    {
                        "url": "https://example.com/",
                        "status": "completed",
                        "metadata": {"status": 200},
                        "markdown": "# Home",
                    },
                    {
                        "url": "https://external.com/",
                        "status": "skipped",
                    },
                ],
            },
        },
    ))

    result = await get_crawl_result(ACCOUNT_ID, API_TOKEN, "job-123")
    assert len(result.pages) == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_crawl_result_pending():
    respx.get(f"{BASE}/job-123").mock(return_value=httpx.Response(
        200,
        json={
            "success": True,
            "result": {
                "id": "job-123",
                "status": "running",
                "records": [],
            },
        },
    ))

    result = await get_crawl_result(ACCOUNT_ID, API_TOKEN, "job-123")
    assert result.status == CrawlStatus.RUNNING
    assert len(result.pages) == 0
