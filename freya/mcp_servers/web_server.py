"""
Web Tools MCP Server for Freya

This server provides web search and scraping tools
using the official MCP Python SDK.
"""

import asyncio
import hashlib
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

from mcp.server import Server
from mcp.types import Tool, TextContent

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# Create server instance
server = Server("freya-web-server")

# Search cache
_search_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 3600.0  # 1 hour


def _get_cache_key(query: str, max_results: int) -> str:
    """Generate cache key for query."""
    normalized = f"{query.lower().strip()}:{max_results}"
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def _get_cached_result(cache_key: str) -> Optional[str]:
    """Get cached search result if valid."""
    if cache_key not in _search_cache:
        return None

    result, timestamp = _search_cache[cache_key]
    age = time.time() - timestamp

    if age > CACHE_TTL:
        del _search_cache[cache_key]
        return None

    return result


def _cache_result(cache_key: str, result: str) -> None:
    """Cache search result with timestamp."""
    _search_cache[cache_key] = (result, time.time())


# ============================================================================
# Tool Definitions
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="web_search",
            description="Search the web for information using DuckDuckGo",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (1-10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="web_scraper",
            description="Scrape and extract content from web pages",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape"
                    },
                    "mode": {
                        "type": "string",
                        "description": "What to extract",
                        "enum": ["text", "links", "title", "headings", "custom"],
                        "default": "text"
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for custom mode"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum length of returned content",
                        "default": 5000
                    }
                },
                "required": ["url"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution."""
    if name == "web_search":
        return await _web_search(
            arguments["query"],
            arguments.get("max_results", 5)
        )
    elif name == "web_scraper":
        return await _web_scraper(
            arguments["url"],
            arguments.get("mode", "text"),
            arguments.get("selector"),
            arguments.get("max_length", 5000)
        )
    else:
        raise ValueError(f"Unknown tool: {name}")


# ============================================================================
# Web Search Implementation
# ============================================================================

async def _web_search(query: str, max_results: int = 5) -> list[TextContent]:
    """Search the web using DuckDuckGo."""
    if DDGS is None:
        return [TextContent(
            type="text",
            text="Error: ddgs not installed. Run: pip install ddgs"
        )]

    if not query or not query.strip():
        return [TextContent(type="text", text="Error: No search query provided")]

    query = query.strip()
    max_results = max(1, min(int(max_results), 10))

    # Check cache first
    cache_key = _get_cache_key(query, max_results)
    cached = _get_cached_result(cache_key)
    if cached is not None:
        return [TextContent(type="text", text=cached)]

    try:
        # Perform search
        ddgs = DDGS()
        results = await asyncio.to_thread(ddgs.text, query, max_results=max_results)

        if not results:
            output = f"No search results found for '{query}'."
        else:
            # Format results
            formatted = []
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                body = result.get("body", "No description")
                href = result.get("href", "")
                formatted.append(f"{i}. {title}\n   {body}\n   {href}")

            output = "\n\n".join(formatted)

        # Cache the result
        _cache_result(cache_key, output)

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: Web search failed: {e}")]


# ============================================================================
# Web Scraper Implementation
# ============================================================================

async def _web_scraper(
    url: str,
    mode: str = "text",
    selector: Optional[str] = None,
    max_length: int = 5000
) -> list[TextContent]:
    """Scrape a web page."""
    if requests is None:
        return [TextContent(
            type="text",
            text="Error: requests library not installed. Run: pip install requests"
        )]

    if BeautifulSoup is None:
        return [TextContent(
            type="text",
            text="Error: beautifulsoup4 library not installed. Run: pip install beautifulsoup4"
        )]

    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return [TextContent(type="text", text=f"Error: Invalid URL: {url}")]

        # Fetch page
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FreyaBot/1.0; +https://github.com/MrPink1977/freya_project)"
        }
        
        response = await asyncio.to_thread(
            requests.get, url, headers=headers, timeout=10
        )
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "aside"]):
            element.decompose()

        # Extract based on mode
        if mode == "title":
            title = soup.find("title")
            output = title.get_text().strip() if title else "No title found"

        elif mode == "links":
            links = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text().strip()
                full_url = urljoin(url, href)
                if text and href:
                    links.append(f"- {text}: {full_url}")

            output = "\n".join(links[:50])
            if not output:
                output = "No links found"

        elif mode == "headings":
            headings = []
            for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                for heading in soup.find_all(tag):
                    text = heading.get_text().strip()
                    if text:
                        headings.append(f"{tag.upper()}: {text}")

            output = "\n".join(headings)
            if not output:
                output = "No headings found"

        elif mode == "custom" and selector:
            elements = soup.select(selector)
            if elements:
                output = "\n\n".join(elem.get_text().strip() for elem in elements)
            else:
                output = f"No elements found matching selector: {selector}"

        else:  # mode == "text" (default)
            # Try to find main content
            main_content = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=re.compile(r"content|article|post|entry"))
                or soup.find("body")
            )

            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
                text = re.sub(r"\n\s*\n", "\n\n", text)
                text = re.sub(r" +", " ", text)
                output = text.strip()
            else:
                output = "Could not extract main content"

        # Truncate if needed
        if len(output) > max_length:
            output = output[:max_length] + f"... (truncated from {len(output)} chars)"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: Scraping failed: {e}")]


# ============================================================================
# Server Entry Point
# ============================================================================

async def main():
    """Run the server using stdio transport."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
