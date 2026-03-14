"""AI-powered diff summarization.

Supports multiple providers: Cloudflare Workers AI, Anthropic, OpenAI.
AI is always optional — diffs work without it.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from crawldiff.core.differ import DiffResult
from crawldiff.utils.config import get_value

SUMMARY_PROMPT = """\
You are analyzing changes to a website. Below are the unified diffs \
showing what changed between two crawls.

Provide a concise, bullet-pointed summary of the meaningful changes. Focus on:
- Content changes (pricing, features, policy updates)
- Structural changes (new pages, removed sections)
- Significant wording changes

Ignore trivial changes like timestamps, session IDs, or whitespace.
Keep each bullet to one sentence. Use plain language a developer would understand.

Diffs:
{diffs}

Summary:"""

MAX_DIFF_CHARS = 12000  # Truncate diffs to stay within token limits


@dataclass
class SummaryConfig:
    """Configuration for AI summary generation."""

    provider: str  # "cloudflare", "anthropic", "openai", "none"
    model: str
    api_key: str
    cf_account_id: str = ""
    cf_api_token: str = ""


def get_summary_config() -> SummaryConfig:
    """Build summary config from stored settings/env vars."""
    provider = get_value("ai.provider") or "none"
    return SummaryConfig(
        provider=provider,
        model=get_value("ai.model") or _default_model(provider),
        api_key=get_value("ai.api_key"),
        cf_account_id=get_value("cloudflare.account_id"),
        cf_api_token=get_value("cloudflare.api_token"),
    )


async def summarize_diff(diff_result: DiffResult, config: SummaryConfig | None = None) -> str:
    """Generate an AI summary of a diff result. Returns empty string if AI is disabled."""
    if config is None:
        config = get_summary_config()

    if config.provider == "none" or not config.provider:
        return ""

    # Build diff text for the prompt
    diff_text = _build_diff_text(diff_result)
    if not diff_text.strip():
        return "No meaningful changes detected."

    prompt = SUMMARY_PROMPT.format(diffs=diff_text[:MAX_DIFF_CHARS])

    if config.provider == "cloudflare":
        return await _summarize_cloudflare(prompt, config)
    elif config.provider == "anthropic":
        return await _summarize_anthropic(prompt, config)
    elif config.provider == "openai":
        return await _summarize_openai(prompt, config)
    else:
        return ""


async def _summarize_cloudflare(prompt: str, config: SummaryConfig) -> str:
    """Use Cloudflare Workers AI for summarization."""
    model = config.model or "@cf/meta/llama-3.1-8b-instruct"
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{config.cf_account_id}/ai/run/{model}"
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {config.cf_api_token}",
                    "Content-Type": "application/json",
                },
                json={"prompt": prompt},
            )
    except Exception as e:  # noqa: BLE001 — catch all API/network errors gracefully
        return f"[AI summary failed: {e}]"

    if resp.status_code != 200:
        return f"[AI summary failed: {resp.status_code}]"

    data: dict[str, object] = resp.json()
    result = data.get("result")
    if isinstance(result, dict):
        response = result.get("response")
        if isinstance(response, str):
            return response
    return "[No summary generated]"


async def _summarize_anthropic(prompt: str, config: SummaryConfig) -> str:
    """Use Anthropic Claude for summarization."""
    try:
        import anthropic
    except ImportError:
        return "[Install 'anthropic' package: pip install crawldiff[ai]]"

    client = anthropic.AsyncAnthropic(api_key=config.api_key)
    model = config.model or "claude-haiku-4-5-20251001"

    try:
        message = await client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:  # noqa: BLE001 — catch all API/network errors gracefully
        return f"[AI summary failed: {e}]"

    if message.content:
        block = message.content[0]
        if hasattr(block, "text"):
            return str(block.text)
    return "[No summary generated]"


async def _summarize_openai(prompt: str, config: SummaryConfig) -> str:
    """Use OpenAI for summarization."""
    try:
        import openai
    except ImportError:
        return "[Install 'openai' package: pip install crawldiff[ai]]"

    client = openai.AsyncOpenAI(api_key=config.api_key)
    model = config.model or "gpt-4o-mini"

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
    except Exception as e:  # noqa: BLE001 — catch all API/network errors gracefully
        return f"[AI summary failed: {e}]"

    choice = response.choices[0] if response.choices else None
    if choice and choice.message and choice.message.content:
        return str(choice.message.content)
    return "[No summary generated]"


def _build_diff_text(diff_result: DiffResult) -> str:
    """Build a text representation of diffs for the AI prompt."""
    parts: list[str] = []

    for page in diff_result.pages_added:
        parts.append(f"NEW PAGE: {page.url}")

    for page in diff_result.pages_removed:
        parts.append(f"REMOVED PAGE: {page.url}")

    for page in diff_result.pages_changed:
        parts.append(f"CHANGED: {page.url}\n{page.unified_diff}")

    return "\n\n".join(parts)


def _default_model(provider: str) -> str:
    """Return the default model for a provider."""
    defaults = {
        "cloudflare": "@cf/meta/llama-3.1-8b-instruct",
        "anthropic": "claude-haiku-4-5-20251001",
        "openai": "gpt-4o-mini",
    }
    return defaults.get(provider, "")
