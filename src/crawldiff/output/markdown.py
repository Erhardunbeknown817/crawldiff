"""Markdown report output for crawldiff diffs."""

from __future__ import annotations

from crawldiff.core.differ import DiffResult


def render_diff_markdown(
    diff_result: DiffResult,
    url: str,
    ai_summary: str = "",
) -> str:
    """Render a diff result as a Markdown report."""
    lines: list[str] = []

    lines.append(f"# crawldiff report — {url}\n")

    # Summary
    lines.append("## Summary\n")
    lines.append(f"- **{len(diff_result.pages_changed)}** pages changed")
    lines.append(f"- **{len(diff_result.pages_added)}** pages added")
    lines.append(f"- **{len(diff_result.pages_removed)}** pages removed")
    lines.append(f"- **{diff_result.pages_unchanged}** pages unchanged")
    lines.append("")

    # AI Summary
    if ai_summary:
        lines.append("## AI Summary\n")
        lines.append(ai_summary)
        lines.append("")

    # Added pages
    if diff_result.pages_added:
        lines.append("## New Pages\n")
        for page in diff_result.pages_added:
            lines.append(f"- {page.url}")
        lines.append("")

    # Removed pages
    if diff_result.pages_removed:
        lines.append("## Removed Pages\n")
        for page in diff_result.pages_removed:
            lines.append(f"- {page.url}")
        lines.append("")

    # Changed pages
    if diff_result.pages_changed:
        lines.append("## Changes\n")
        for page in diff_result.pages_changed:
            lines.append(f"### {page.url}\n")
            lines.append("```diff")
            lines.append(page.unified_diff)
            lines.append("```\n")

    return "\n".join(lines)
