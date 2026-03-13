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


@pytest.mark.asyncio
async def test_summarize_anthropic():
    """Test Anthropic Claude summarization with mocked client."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_block = MagicMock()
    mock_block.text = "Pricing increased from $25 to $30."

    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client

    config = SummaryConfig(
        provider="anthropic", model="claude-haiku-4-5-20251001",
        api_key="sk-test-123",
    )

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        result = await summarize_diff(_make_diff_result(), config)

    assert "Pricing" in result or "pricing" in result


@pytest.mark.asyncio
async def test_summarize_anthropic_api_error():
    """Anthropic API error should return error message, not crash."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("Invalid API key"))

    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client

    config = SummaryConfig(
        provider="anthropic", model="claude-haiku-4-5-20251001",
        api_key="bad-key",
    )

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        result = await summarize_diff(_make_diff_result(), config)

    assert "failed" in result.lower()


@pytest.mark.asyncio
async def test_summarize_anthropic_empty_content():
    """Anthropic returning empty content should not crash."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_message = MagicMock()
    mock_message.content = []

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    mock_anthropic = MagicMock()
    mock_anthropic.AsyncAnthropic.return_value = mock_client

    config = SummaryConfig(
        provider="anthropic", model="claude-haiku-4-5-20251001",
        api_key="sk-test",
    )

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        result = await summarize_diff(_make_diff_result(), config)

    assert "No summary generated" in result


@pytest.mark.asyncio
async def test_summarize_openai():
    """Test OpenAI summarization with mocked client."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_message = MagicMock()
    mock_message.content = "Pricing went up. New blog page added."

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_openai = MagicMock()
    mock_openai.AsyncOpenAI.return_value = mock_client

    config = SummaryConfig(
        provider="openai", model="gpt-4o-mini",
        api_key="sk-test-123",
    )

    with patch.dict("sys.modules", {"openai": mock_openai}):
        result = await summarize_diff(_make_diff_result(), config)

    assert "Pricing" in result or "pricing" in result


@pytest.mark.asyncio
async def test_summarize_openai_api_error():
    """OpenAI API error should return error message, not crash."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("Rate limit exceeded")
    )

    mock_openai = MagicMock()
    mock_openai.AsyncOpenAI.return_value = mock_client

    config = SummaryConfig(
        provider="openai", model="gpt-4o-mini",
        api_key="bad-key",
    )

    with patch.dict("sys.modules", {"openai": mock_openai}):
        result = await summarize_diff(_make_diff_result(), config)

    assert "failed" in result.lower()


@pytest.mark.asyncio
async def test_summarize_openai_empty_choices():
    """OpenAI returning empty choices should not crash."""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_response = MagicMock()
    mock_response.choices = []

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_openai = MagicMock()
    mock_openai.AsyncOpenAI.return_value = mock_client

    config = SummaryConfig(
        provider="openai", model="gpt-4o-mini",
        api_key="sk-test",
    )

    with patch.dict("sys.modules", {"openai": mock_openai}):
        result = await summarize_diff(_make_diff_result(), config)

    assert "No summary generated" in result
