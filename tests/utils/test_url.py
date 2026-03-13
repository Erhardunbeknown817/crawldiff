"""Tests for URL normalization utilities."""

from __future__ import annotations

from crawldiff.utils.url import get_domain, normalize_url


def test_normalize_adds_https():
    assert normalize_url("example.com") == "https://example.com/"


def test_normalize_preserves_http():
    assert normalize_url("http://example.com") == "http://example.com/"


def test_normalize_strips_trailing_slash():
    assert normalize_url("https://example.com/about/") == "https://example.com/about"


def test_normalize_lowercases_hostname():
    assert normalize_url("https://EXAMPLE.COM/About") == "https://example.com/About"


def test_normalize_preserves_path():
    assert normalize_url("https://example.com/a/b/c") == "https://example.com/a/b/c"


def test_normalize_preserves_query():
    assert normalize_url("https://example.com/search?q=test") == "https://example.com/search?q=test"


def test_normalize_drops_fragment():
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_preserves_port():
    assert normalize_url("https://example.com:8080/api") == "https://example.com:8080/api"


def test_normalize_root_path():
    assert normalize_url("https://example.com") == "https://example.com/"


def test_get_domain_basic():
    assert get_domain("https://example.com/about") == "example.com"


def test_get_domain_without_scheme():
    assert get_domain("example.com") == "example.com"


def test_get_domain_with_subdomain():
    assert get_domain("https://blog.example.com/post") == "blog.example.com"
