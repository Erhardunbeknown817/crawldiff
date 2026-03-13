"""Tests for the Cloudflare /crawl API client."""

from __future__ import annotations

from datetime import UTC

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
        json={"success": True, "result": {"id": "job-abc-123"}},
    ))

    job_id = await start_crawl(ACCOUNT_ID, API_TOKEN, "https://example.com")
    assert job_id == "job-abc-123"


@pytest.mark.asyncio
@respx.mock
async def test_start_crawl_sends_correct_body():
    route = respx.post(BASE).mock(return_value=httpx.Response(
        200,
        json={"success": True, "result": {"id": "job-123"}},
    ))

    await start_crawl(
        ACCOUNT_ID, API_TOKEN, "https://example.com",
        depth=3, max_pages=100,
    )

    request = route.calls[0].request
    import json
    body = json.loads(request.content)
    assert body["url"] == "https://example.com"
    assert body["maxDepth"] == 3
    assert body["maxPages"] == 100
    assert body["scrapeOptions"]["formats"] == ["markdown"]


@pytest.mark.asyncio
@respx.mock
async def test_start_crawl_with_modified_since():
    from datetime import datetime

    route = respx.post(BASE).mock(return_value=httpx.Response(
        200,
        json={"success": True, "result": {"id": "job-123"}},
    ))

    since = datetime(2026, 3, 10, 0, 0, 0, tzinfo=UTC)
    await start_crawl(
        ACCOUNT_ID, API_TOKEN, "https://example.com",
        modified_since=since,
    )

    import json
    body = json.loads(route.calls[0].request.content)
    assert "modifiedSince" in body
    assert "2026-03-10" in body["modifiedSince"]


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
                "status": "complete",
                "totalPages": 2,
                "pages": [
                    {
                        "url": "https://example.com/",
                        "markdown": "# Home",
                        "html": "<h1>Home</h1>",
                        "status_code": 200,
                    },
                    {
                        "url": "https://example.com/about",
                        "markdown": "# About",
                        "html": "<h1>About</h1>",
                        "status_code": 200,
                    },
                ],
            },
        },
    ))

    result = await get_crawl_result(ACCOUNT_ID, API_TOKEN, "job-123")
    assert result.status == CrawlStatus.COMPLETE
    assert len(result.pages) == 2
    assert result.pages[0].url == "https://example.com/"
    assert result.pages[0].markdown == "# Home"


@pytest.mark.asyncio
@respx.mock
async def test_get_crawl_result_pending():
    respx.get(f"{BASE}/job-123").mock(return_value=httpx.Response(
        200,
        json={
            "success": True,
            "result": {"id": "job-123", "status": "running", "pages": []},
        },
    ))

    result = await get_crawl_result(ACCOUNT_ID, API_TOKEN, "job-123")
    assert result.status == CrawlStatus.RUNNING
    assert len(result.pages) == 0
