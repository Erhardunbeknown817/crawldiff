"""Tests for Markdown report output."""

from __future__ import annotations

from crawldiff.core.differ import ChangeType, DiffResult, PageDiff
from crawldiff.output.markdown import render_diff_markdown


def _make_diff_result(
    added: list[str] | None = None,
    removed: list[str] | None = None,
    changed: list[tuple[str, str]] | None = None,
    unchanged: int = 0,
) -> DiffResult:
    return DiffResult(
        pages_added=[PageDiff(url=u, change_type=ChangeType.ADDED) for u in (added or [])],
        pages_removed=[PageDiff(url=u, change_type=ChangeType.REMOVED) for u in (removed or [])],
        pages_changed=[
            PageDiff(url=u, change_type=ChangeType.MODIFIED, unified_diff=d)
            for u, d in (changed or [])
        ],
        pages_unchanged=unchanged,
    )


def test_markdown_header():
    result = _make_diff_result()
    md = render_diff_markdown(result, "https://example.com")
    assert "# crawldiff report — https://example.com" in md


def test_markdown_summary_counts():
    result = _make_diff_result(
        added=["https://example.com/new"],
        removed=["https://example.com/old"],
        changed=[("https://example.com/", "diff")],
        unchanged=3,
    )
    md = render_diff_markdown(result, "https://example.com")
    assert "**1** pages changed" in md
    assert "**1** pages added" in md
    assert "**1** pages removed" in md
    assert "**3** pages unchanged" in md


def test_markdown_added_pages():
    result = _make_diff_result(added=["https://example.com/blog"])
    md = render_diff_markdown(result, "https://example.com")
    assert "## New Pages" in md
    assert "https://example.com/blog" in md


def test_markdown_removed_pages():
    result = _make_diff_result(removed=["https://example.com/old"])
    md = render_diff_markdown(result, "https://example.com")
    assert "## Removed Pages" in md
    assert "https://example.com/old" in md


def test_markdown_changed_pages():
    result = _make_diff_result(changed=[("https://example.com/", "-old\n+new")])
    md = render_diff_markdown(result, "https://example.com")
    assert "## Changes" in md
    assert "```diff" in md
    assert "-old\n+new" in md


def test_markdown_ai_summary():
    result = _make_diff_result()
    md = render_diff_markdown(result, "https://example.com", ai_summary="Prices changed.")
    assert "## AI Summary" in md
    assert "Prices changed." in md


def test_markdown_no_ai_summary():
    result = _make_diff_result()
    md = render_diff_markdown(result, "https://example.com")
    assert "## AI Summary" not in md
