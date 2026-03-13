"""Tests for terminal output functions."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from rich.console import Console

from crawldiff.core.differ import ChangeType, DiffResult, PageDiff
from crawldiff.output.terminal import (
    print_config_table,
    print_crawl_summary,
    print_diff_result,
    print_error,
    print_history_table,
    print_success,
)


def _capture(func, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
    """Capture rich console output as plain text."""
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=True, width=120)
    with patch("crawldiff.output.terminal.console", test_console):
        func(*args, **kwargs)
    return buf.getvalue()


def _capture_stderr(func, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
    """Capture stderr rich console output."""
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=True, width=120)
    with patch("crawldiff.output.terminal.err_console", test_console):
        func(*args, **kwargs)
    return buf.getvalue()


def test_print_crawl_summary():
    output = _capture(print_crawl_summary, "https://example.com", 15, 3.2)
    assert "15" in output
    assert "3.2" in output


def test_print_diff_result_no_changes():
    result = DiffResult()
    output = _capture(print_diff_result, result, "https://example.com")
    assert "No changes" in output


def test_print_diff_result_with_changes():
    result = DiffResult(
        pages_added=[PageDiff(url="https://example.com/new", change_type=ChangeType.ADDED)],
        pages_changed=[
            PageDiff(
                url="https://example.com/",
                change_type=ChangeType.MODIFIED,
                unified_diff="-old\n+new",
            ),
        ],
        pages_removed=[PageDiff(url="https://example.com/old", change_type=ChangeType.REMOVED)],
        pages_unchanged=2,
    )
    output = _capture(print_diff_result, result, "https://example.com")
    assert "1 changed" in output
    assert "1 added" in output
    assert "1 removed" in output
    assert "NEW PAGE" in output
    assert "REMOVED" in output
    assert "CHANGED" in output


def test_print_diff_result_with_ai_summary():
    result = DiffResult(
        pages_changed=[
            PageDiff(
                url="https://example.com/",
                change_type=ChangeType.MODIFIED,
                unified_diff="-a\n+b",
            ),
        ],
    )
    output = _capture(
        print_diff_result, result, "https://example.com", ai_summary="Prices changed."
    )
    assert "AI Summary" in output
    assert "Prices changed." in output


def test_print_history_table_with_data():
    rows: list[dict[str, str | int]] = [
        {"job_id": "job-123", "crawled_at": "2026-03-14", "page_count": 10},
        {"job_id": "job-456", "crawled_at": "2026-03-13", "page_count": 8},
    ]
    output = _capture(print_history_table, rows, "https://example.com")
    assert "job-123" in output
    assert "job-456" in output
    assert "Crawl History" in output


def test_print_history_table_empty():
    output = _capture(print_history_table, [], "https://example.com")
    assert "No crawl history" in output


def test_print_config_table():
    config = {"ai.provider": "anthropic", "cloudflare.account_id": "****1234"}
    output = _capture(print_config_table, config)
    assert "ai.provider" in output
    assert "anthropic" in output


def test_print_error():
    output = _capture_stderr(print_error, "Something went wrong")
    assert "Error" in output
    assert "Something went wrong" in output


def test_print_success():
    output = _capture(print_success, "Config saved")
    assert "Config saved" in output
