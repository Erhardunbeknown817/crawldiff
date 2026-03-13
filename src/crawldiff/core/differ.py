"""Diffing engine for comparing website snapshots.

Compares markdown content page-by-page and produces unified diffs.
Uses stdlib difflib — no external dependencies.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from enum import Enum

from crawldiff.core.storage import PageSnapshot


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class PageDiff:
    """Diff result for a single page."""

    url: str
    change_type: ChangeType
    unified_diff: str = ""
    old_hash: str = ""
    new_hash: str = ""


@dataclass
class DiffResult:
    """Full diff result comparing two sets of snapshots."""

    pages_added: list[PageDiff] = field(default_factory=list)
    pages_removed: list[PageDiff] = field(default_factory=list)
    pages_changed: list[PageDiff] = field(default_factory=list)
    pages_unchanged: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(self.pages_added or self.pages_removed or self.pages_changed)

    @property
    def total_changes(self) -> int:
        return len(self.pages_added) + len(self.pages_removed) + len(self.pages_changed)


def diff_snapshots(
    old_pages: list[PageSnapshot],
    new_pages: list[PageSnapshot],
    *,
    ignore_whitespace: bool = False,
    context_lines: int = 3,
) -> DiffResult:
    """Compare two sets of page snapshots and produce a DiffResult."""
    old_map = {p.url: p for p in old_pages}
    new_map = {p.url: p for p in new_pages}

    old_urls = set(old_map.keys())
    new_urls = set(new_map.keys())

    result = DiffResult()

    # Added pages (in new, not in old)
    for url in sorted(new_urls - old_urls):
        page = new_map[url]
        result.pages_added.append(PageDiff(
            url=url,
            change_type=ChangeType.ADDED,
            new_hash=page.content_hash,
        ))

    # Removed pages (in old, not in new)
    for url in sorted(old_urls - new_urls):
        page = old_map[url]
        result.pages_removed.append(PageDiff(
            url=url,
            change_type=ChangeType.REMOVED,
            old_hash=page.content_hash,
        ))

    # Modified or unchanged pages (in both)
    for url in sorted(old_urls & new_urls):
        old_page = old_map[url]
        new_page = new_map[url]

        # Quick hash check
        if old_page.content_hash == new_page.content_hash:
            result.pages_unchanged += 1
            continue

        # Generate unified diff
        old_content = old_page.content_md or ""
        new_content = new_page.content_md or ""

        if ignore_whitespace:
            old_lines = _normalize_whitespace(old_content).splitlines(keepends=True)
            new_lines = _normalize_whitespace(new_content).splitlines(keepends=True)
        else:
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{url}",
            tofile=f"b/{url}",
            n=context_lines,
        ))

        if diff_lines:
            result.pages_changed.append(PageDiff(
                url=url,
                change_type=ChangeType.MODIFIED,
                unified_diff="".join(diff_lines),
                old_hash=old_page.content_hash,
                new_hash=new_page.content_hash,
            ))
        else:
            # Whitespace-only diff after normalization
            result.pages_unchanged += 1

    return result


def _normalize_whitespace(text: str) -> str:
    """Collapse whitespace for comparison."""
    lines = text.splitlines()
    return "\n".join(line.strip() for line in lines)
