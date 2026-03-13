"""Tests for the AI summarizer."""

from __future__ import annotations

import httpx
import pytest
import respx

from crawldiff.core.differ import ChangeType, DiffResult, PageDiff
from crawldiff.core.summarizer import SummaryConfig, summarize_diff


def _make_diff_result() -> DiffResult:
    """Create a sample diff result for testing."""
    return DiffResult(
        pages_changed=[
            PageDiff(
                url="https://example.com/pricing",
                change_type=ChangeType.MODIFIED,
                unified_diff="--- a/pricing\n+++ b/pricing\n-$25/mo\n+$30/mo",
            )
        ],
        pages_added=[
            PageDiff(url="https://example.com/blog", change_type=ChangeType.ADDED)
        ],
    )


@pytest.mark.asyncio
async def test_summarize_with_none_provider():
    """Provider 'none' should return empty string."""
    config = SummaryConfig(provider="none", model="", api_key="")
    result = await summarize_diff(_make_diff_result(), config)
    assert result == ""


@pytest.mark.asyncio
async def test_summarize_with_empty_provider():
    """Empty provider should return empty string."""
    config = SummaryConfig(provider="", model="", api_key="")
    result = await summarize_diff(_make_diff_result(), config)
    assert result == ""


@pytest.mark.asyncio
@respx.mock
async def test_summarize_cloudflare():
    """Test Cloudflare Workers AI summarization."""
    url = "https://api.cloudflare.com/client/v4/accounts/acc-123/ai/run/@cf/meta/llama-3.1-8b-instruct"
    respx.post(url).mock(return_value=httpx.Response(
        200,
        json={"result": {"response": "Pricing increased from $25 to $30. New blog page added."}},
    ))

    config = SummaryConfig(
        provider="cloudflare",
        model="@cf/meta/llama-3.1-8b-instruct",
        api_key="",
        cf_account_id="acc-123",
        cf_api_token="tok-456",
    )

    result = await summarize_diff(_make_diff_result(), config)
    assert "Pricing" in result or "pricing" in result


@pytest.mark.asyncio
@respx.mock
async def test_summarize_cloudflare_error():
    """Cloudflare error should return error message, not crash."""
    url = "https://api.cloudflare.com/client/v4/accounts/acc-123/ai/run/@cf/meta/llama-3.1-8b-instruct"
    respx.post(url).mock(return_value=httpx.Response(500))

    config = SummaryConfig(
        provider="cloudflare",
        model="@cf/meta/llama-3.1-8b-instruct",
        api_key="",
        cf_account_id="acc-123",
        cf_api_token="tok-456",
    )

    result = await summarize_diff(_make_diff_result(), config)
    assert "failed" in result.lower()


@pytest.mark.asyncio
async def test_summarize_no_changes():
    """Empty diff should return 'no changes' message."""
    config = SummaryConfig(
        provider="cloudflare", model="", api_key="",
        cf_account_id="x", cf_api_token="x",
    )
    empty_diff = DiffResult()
    result = await summarize_diff(empty_diff, config)
    assert "no meaningful changes" in result.lower() or result == ""
