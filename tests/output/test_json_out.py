"""Tests for JSON output."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from crawldiff.core.differ import ChangeType, DiffResult, PageDiff
from crawldiff.output.json_out import print_diff_json


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


def test_json_output_structure():
    result = _make_diff_result(
        added=["https://example.com/new"],
        removed=["https://example.com/old"],
        changed=[("https://example.com/", "-old\n+new")],
        unchanged=2,
    )
    buf = StringIO()
    with patch("crawldiff.output.json_out.sys.stdout", buf):
        print_diff_json(result, "https://example.com")

    data = json.loads(buf.getvalue())
    assert data["url"] == "https://example.com"
    assert data["summary"]["pages_added"] == 1
    assert data["summary"]["pages_removed"] == 1
    assert data["summary"]["pages_changed"] == 1
    assert data["summary"]["pages_unchanged"] == 2
    assert len(data["added"]) == 1
    assert len(data["removed"]) == 1
    assert len(data["changed"]) == 1
    assert "ai_summary" not in data


def test_json_output_with_ai_summary():
    result = _make_diff_result()
    buf = StringIO()
    with patch("crawldiff.output.json_out.sys.stdout", buf):
        print_diff_json(result, "https://example.com", ai_summary="Price went up.")

    data = json.loads(buf.getvalue())
    assert data["ai_summary"] == "Price went up."


def test_json_output_no_changes():
    result = _make_diff_result(unchanged=5)
    buf = StringIO()
    with patch("crawldiff.output.json_out.sys.stdout", buf):
        print_diff_json(result, "https://example.com")

    data = json.loads(buf.getvalue())
    assert data["summary"]["pages_unchanged"] == 5
    assert data["added"] == []
    assert data["removed"] == []
    assert data["changed"] == []
