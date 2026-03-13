"""JSON output for piping and scripting."""

from __future__ import annotations

import json
import sys

from crawldiff.core.differ import DiffResult


def print_diff_json(
    diff_result: DiffResult,
    url: str,
    ai_summary: str = "",
) -> None:
    """Write diff result as JSON to stdout."""
    output = {
        "url": url,
        "summary": {
            "pages_added": len(diff_result.pages_added),
            "pages_removed": len(diff_result.pages_removed),
            "pages_changed": len(diff_result.pages_changed),
            "pages_unchanged": diff_result.pages_unchanged,
        },
        "added": [{"url": p.url} for p in diff_result.pages_added],
        "removed": [{"url": p.url} for p in diff_result.pages_removed],
        "changed": [
            {
                "url": p.url,
                "diff": p.unified_diff,
            }
            for p in diff_result.pages_changed
        ],
    }
    if ai_summary:
        output["ai_summary"] = ai_summary

    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")
