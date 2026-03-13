"""Tests for the diff CLI command."""

from __future__ import annotations

from datetime import timedelta

import pytest
import typer

from crawldiff.utils.duration import parse_duration as _parse_duration


def test_parse_duration_minutes():
    assert _parse_duration("30m") == timedelta(minutes=30)


def test_parse_duration_hours():
    assert _parse_duration("1h") == timedelta(hours=1)
    assert _parse_duration("24h") == timedelta(hours=24)


def test_parse_duration_days():
    assert _parse_duration("7d") == timedelta(days=7)
    assert _parse_duration("30d") == timedelta(days=30)


def test_parse_duration_weeks():
    assert _parse_duration("2w") == timedelta(weeks=2)


def test_parse_duration_invalid():
    with pytest.raises(typer.BadParameter):
        _parse_duration("abc")


def test_parse_duration_no_unit():
    with pytest.raises(typer.BadParameter):
        _parse_duration("30")


def test_parse_duration_with_spaces():
    assert _parse_duration("  7d  ") == timedelta(days=7)
