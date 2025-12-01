"""Tests for web search rate limiting and caching."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from freya.tools.web_search import (
    CACHE_TTL,
    RateLimitError,
    _cache_result,
    _get_cache_key,
    _get_cached_result,
    clear_search_cache,
    get_cache_stats,
    search_web_async,
)


class TestCacheFunctions:
    """Test search caching utilities."""

    def test_cache_key_normalized(self):
        """Cache keys are normalized."""
        key1 = _get_cache_key("Python Tutorial", 5)
        key2 = _get_cache_key("python tutorial", 5)
        key3 = _get_cache_key("  PYTHON TUTORIAL  ", 5)

        assert key1 == key2 == key3

    def test_cache_key_includes_max_results(self):
        """Cache keys include max_results parameter."""
        key1 = _get_cache_key("test query", 5)
        key2 = _get_cache_key("test query", 10)

        assert key1 != key2

    def test_cache_miss_returns_none(self):
        """Cache miss returns None."""
        clear_search_cache()
        result = _get_cached_result("nonexistent_key")
        assert result is None

    def test_cache_hit_returns_result(self):
        """Cache hit returns stored result."""
        clear_search_cache()
        cache_key = _get_cache_key("test", 5)

        _cache_result(cache_key, "cached data")
        result = _get_cached_result(cache_key)

        assert result == "cached data"

    def test_expired_cache_removed(self):
        """Expired cache entries are removed."""
        clear_search_cache()
        cache_key = _get_cache_key("test", 5)

        # Manually insert expired entry
        from freya.tools.web_search import _search_cache
        _search_cache[cache_key] = ("old data", time.time() - CACHE_TTL - 1)

        result = _get_cached_result(cache_key)
        assert result is None
        assert cache_key not in _search_cache

    def test_clear_cache_empties_dict(self):
        """clear_search_cache removes all entries."""
        _cache_result("key1", "data1")
        _cache_result("key2", "data2")

        clear_search_cache()
        stats = get_cache_stats()

        assert stats["size"] == 0

    def test_cache_stats_empty(self):
        """Cache stats for empty cache."""
        clear_search_cache()
        stats = get_cache_stats()

        assert stats["size"] == 0
        assert stats["oldest_age"] == 0.0

    def test_cache_stats_with_entries(self):
        """Cache stats with entries."""
        clear_search_cache()
        _cache_result("key1", "data1")
        time.sleep(0.1)
        _cache_result("key2", "data2")

        stats = get_cache_stats()

        assert stats["size"] == 2
        assert stats["oldest_age"] > 0.0


class TestWebSearchAsync:
    """Test async web search with rate limiting and caching."""

    @pytest.mark.asyncio
    async def test_cache_prevents_duplicate_requests(self):
        """Cached results prevent duplicate API calls."""
        clear_search_cache()

        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [
            {"title": "Test", "body": "Description", "href": "http://test.com"}
        ]

        with patch("freya.tools.web_search.DDGS", return_value=mock_ddgs):
            # First call - should hit API
            result1 = await search_web_async("test query", 5, use_cache=True)

            # Second call - should use cache
            result2 = await search_web_async("test query", 5, use_cache=True)

            assert result1 == result2
            assert mock_ddgs.text.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_cache_disabled_allows_duplicates(self):
        """use_cache=False bypasses cache."""
        clear_search_cache()

        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [
            {"title": "Test", "body": "Description", "href": "http://test.com"}
        ]

        with patch("freya.tools.web_search.DDGS", return_value=mock_ddgs):
            await search_web_async("test query", 5, use_cache=False)
            await search_web_async("test query", 5, use_cache=False)

            assert mock_ddgs.text.call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self):
        """Rate limiting delays rapid requests."""
        clear_search_cache()

        # Reset rate limiter to known state
        from freya.tools.web_search import _rate_limiter
        _rate_limiter._tokens = float(_rate_limiter.burst)
        _rate_limiter._last_update = time.monotonic()

        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [
            {"title": "Test", "body": "Desc", "href": "http://test.com"}
        ]

        with patch("freya.tools.web_search.DDGS", return_value=mock_ddgs):
            # Make 4 unique requests rapidly (should hit rate limit after burst of 3)
            start = time.monotonic()
            for i in range(4):
                await search_web_async(f"query {i}", 5, use_cache=False, timeout=10.0)
            elapsed = time.monotonic() - start

            # Should take some time due to rate limiting
            # (3 burst immediate + 1 waiting for token)
            assert elapsed > 5.0  # Should wait ~6 seconds for 4th request

    @pytest.mark.asyncio
    async def test_timeout_raises_rate_limit_error(self):
        """Short timeout raises RateLimitError."""
        clear_search_cache()

        # Reset rate limiter by creating many requests

        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = []

        with patch("freya.tools.web_search.DDGS", return_value=mock_ddgs):
            # Exhaust rate limiter with burst
            for i in range(5):
                try:
                    await search_web_async(f"query {i}", 5, use_cache=False, timeout=5.0)
                except Exception:
                    pass

            # Next request should timeout quickly
            with pytest.raises(RateLimitError, match="timeout"):
                await search_web_async("final query", 5, use_cache=False, timeout=0.01)

    @pytest.mark.asyncio
    async def test_handles_no_results(self):
        """Handles empty search results."""
        clear_search_cache()

        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = []

        with patch("freya.tools.web_search.DDGS", return_value=mock_ddgs):
            result = await search_web_async("nonexistent query", 5)

            assert "No search results found" in result

    @pytest.mark.asyncio
    async def test_formats_results_correctly(self):
        """Results are formatted properly."""
        clear_search_cache()

        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [
            {"title": "Title 1", "body": "Body 1", "href": "http://1.com"},
            {"title": "Title 2", "body": "Body 2", "href": "http://2.com"},
        ]

        with patch("freya.tools.web_search.DDGS", return_value=mock_ddgs):
            result = await search_web_async("test", 2)

            assert "Title 1" in result
            assert "Body 1" in result
            assert "http://1.com" in result
            assert "Title 2" in result
