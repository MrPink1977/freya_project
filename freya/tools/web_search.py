"""Web search functionality using DuckDuckGo with rate limiting and caching."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Optional

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from ..logger import get_logger
from ..utils.rate_limiter import TokenBucketRateLimiter, RateLimitError
from ..utils.circuit_breaker import CircuitBreaker

logger = get_logger("web_search")


# Global rate limiter: 10 requests per minute with burst of 3
_rate_limiter = TokenBucketRateLimiter(rate=10, burst=3, time_window=60.0)

# Global circuit breaker for web search
_circuit_breaker = CircuitBreaker(
    failure_threshold=0.5,
    recovery_timeout=60.0,
    window_size=10,
    name="web_search"
)

# Global cache: stores (result, timestamp) tuples
_search_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 3600.0  # 1 hour cache TTL


class WebSearchError(RuntimeError):
    """Raised when web search fails."""


def _get_cache_key(query: str, max_results: int) -> str:
    """
    Generate cache key for query.

    Args:
        query: Search query (normalized)
        max_results: Maximum results count

    Returns:
        MD5 hash of normalized query + max_results
    """
    normalized = f"{query.lower().strip()}:{max_results}"
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def _get_cached_result(cache_key: str) -> Optional[str]:
    """
    Get cached search result if valid.

    Args:
        cache_key: Cache key for lookup

    Returns:
        Cached result if found and not expired, None otherwise
    """
    if cache_key not in _search_cache:
        return None

    result, timestamp = _search_cache[cache_key]
    age = time.time() - timestamp

    if age > CACHE_TTL:
        # Expired, remove from cache
        del _search_cache[cache_key]
        logger.debug("Cache expired for key %s (age: %.1fs)", cache_key[:8], age)
        return None

    logger.debug("Cache hit for key %s (age: %.1fs)", cache_key[:8], age)
    return result


def _cache_result(cache_key: str, result: str) -> None:
    """
    Cache search result with timestamp.

    Args:
        cache_key: Cache key
        result: Search result to cache
    """
    _search_cache[cache_key] = (result, time.time())
    logger.debug("Cached result for key %s", cache_key[:8])


def clear_search_cache() -> None:
    """Clear all cached search results."""
    _search_cache.clear()
    logger.info("Search cache cleared")


def get_cache_stats() -> dict[str, int | float]:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache size and oldest entry age
    """
    if not _search_cache:
        return {"size": 0, "oldest_age": 0.0}

    oldest_timestamp = min(ts for _, ts in _search_cache.values())
    oldest_age = time.time() - oldest_timestamp

    return {"size": len(_search_cache), "oldest_age": oldest_age}


async def search_web_async(
    query: str, max_results: int = 5, use_cache: bool = True, timeout: float = 10.0
) -> str:
    """
    Search DuckDuckGo asynchronously with rate limiting and caching.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        use_cache: Whether to use cached results (default: True)
        timeout: Rate limiter timeout in seconds (default: 10.0)

    Returns:
        Formatted search results as string

    Raises:
        WebSearchError: If search fails or DuckDuckGo not available
        RateLimitError: If rate limit exceeded and timeout expires
    """
    if DDGS is None:
        raise WebSearchError("ddgs not installed. Run: pip install ddgs")

    if not query or not query.strip():
        return "No search query provided."

    query = query.strip()
    max_results = max(1, min(int(max_results), 10))  # Limit 1-10

    # Check cache first
    cache_key = _get_cache_key(query, max_results)
    if use_cache:
        cached = _get_cached_result(cache_key)
        if cached is not None:
            return cached

    # Apply rate limiting
    try:
        await _rate_limiter.acquire(timeout=timeout)
    except RateLimitError:
        logger.warning("Rate limit exceeded for query: %s", query)
        raise

    # Execute search with circuit breaker protection
    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, WebSearchError)),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _perform_search():
        try:
            logger.info("Searching web for: %s", query)
            ddgs = DDGS()
            results = ddgs.text(query, max_results=max_results)

            if not results:
                logger.warning("No results found for: %s", query)
                output = f"No search results found for '{query}'."
            else:
                # Format results for Freya
                formatted = []
                for i, result in enumerate(results, 1):
                    title = result.get("title", "No title")
                    body = result.get("body", "No description")
                    href = result.get("href", "")

                    formatted.append(f"{i}. {title}\n" f"   {body}\n" f"   {href}")

                output = "\n\n".join(formatted)
                logger.debug("Found %d results for '%s'", len(results), query)

            # Cache the result
            if use_cache:
                _cache_result(cache_key, output)

            return output

        except Exception as exc:
            logger.exception("Web search failed: %s", exc)
            raise WebSearchError(f"Search failed: {exc}") from exc
    
    return await _circuit_breaker.call(_perform_search)


def search_web(query: str, max_results: int = 5, use_cache: bool = True) -> str:
    """
    Search DuckDuckGo synchronously (wrapper for async version).

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        use_cache: Whether to use cached results (default: True)

    Returns:
        Formatted search results as string

    Raises:
        WebSearchError: If search fails or DuckDuckGo not available
        RateLimitError: If rate limit exceeded
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(search_web_async(query, max_results, use_cache))
    else:
        # Already in async context, run in executor
        future = loop.run_in_executor(
            None, lambda: asyncio.run(search_web_async(query, max_results, use_cache))
        )
        return asyncio.run_coroutine_threadsafe(
            search_web_async(query, max_results, use_cache), loop
        ).result()


from .base import FreyaTool, ToolResult


class WebSearchTool(FreyaTool):
    """Search the web using DuckDuckGo."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information using DuckDuckGo. Returns up to 5 results with titles, snippets, and URLs."

    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        """Execute web search.

        Args:
            query: Search query string
            max_results: Maximum number of results (1-10, default 5)

        Returns:
            ToolResult with search results
        """
        try:
            output = search_web(query, max_results=max_results, use_cache=True)
            return ToolResult(
                success=True,
                output=output,
                metadata={"query": query, "max_results": max_results}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Web search failed: {e}"
            )


__all__ = [
    "search_web",
    "search_web_async",
    "WebSearchTool",
    "WebSearchError",
    "clear_search_cache",
    "get_cache_stats",
]
