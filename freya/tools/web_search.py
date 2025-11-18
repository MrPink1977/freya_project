"""Web search functionality using DuckDuckGo."""

from __future__ import annotations

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None  # type: ignore[assignment,misc]

from ..logger import get_logger

logger = get_logger("web_search")


class WebSearchError(RuntimeError):
    """Raised when web search fails."""


def search_web(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo and return formatted results.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results as string

    Raises:
        WebSearchError: If search fails or DuckDuckGo not available
    """
    if DDGS is None:
        raise WebSearchError(
            "duckduckgo-search not installed. Run: pip install duckduckgo-search"
        )

    if not query or not query.strip():
        return "No search query provided."

    query = query.strip()
    max_results = max(1, min(int(max_results), 10))  # Limit 1-10

    try:
        logger.info("Searching web for: %s", query)
        ddgs = DDGS()
        results = ddgs.text(query, max_results=max_results)

        if not results:
            logger.warning("No results found for: %s", query)
            return f"No search results found for '{query}'."

        # Format results for Freya
        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            body = result.get("body", "No description")
            href = result.get("href", "")

            formatted.append(
                f"{i}. {title}\n"
                f"   {body}\n"
                f"   {href}"
            )

        output = "\n\n".join(formatted)
        logger.debug("Found %d results for '%s'", len(results), query)
        return output

    except Exception as exc:
        logger.exception("Web search failed: %s", exc)
        raise WebSearchError(f"Search failed: {exc}") from exc


__all__ = ["search_web", "WebSearchError"]
