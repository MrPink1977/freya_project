"""Web scraping tools for Freya."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..logger import get_logger
from .base import FreyaTool, ToolResult

logger = get_logger("web_scraper")


class WebScraperTool(FreyaTool):
    """Scrape and extract content from web pages."""

    @property
    def name(self) -> str:
        return "web_scraper"

    @property
    def description(self) -> str:
        return "Scrape and extract text content, links, or specific elements from web pages"

    def execute(
        self, url: str, mode: str = "text", selector: str | None = None, max_length: int = 5000
    ) -> ToolResult:
        """Scrape a web page.

        Args:
            url: URL to scrape
            mode: What to extract - 'text' (main content), 'links' (all links),
                  'title' (page title), 'headings' (h1-h6), 'custom' (use selector)
            selector: CSS selector for custom mode (e.g., '.article-content', '#main')
            max_length: Maximum length of returned content

        Returns:
            ToolResult with scraped content
        """
        if requests is None:
            return ToolResult(
                success=False,
                output="",
                error="requests library not installed. Run: pip install requests",
            )

        if BeautifulSoup is None:
            return ToolResult(
                success=False,
                output="",
                error="beautifulsoup4 library not installed. Run: pip install beautifulsoup4",
            )

        try:
            return self._execute_with_retry(url, mode, selector, max_length)
        except Exception as exc:
            logger.exception("Web scraping failed for %s: %s", url, exc)
            return ToolResult(success=False, output="", error=f"Scraping failed: {exc}")

    @retry(
        retry=retry_if_exception_type((requests.RequestException, ConnectionError, TimeoutError)),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=2),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )
    def _execute_with_retry(
        self, url: str, mode: str, selector: str | None, max_length: int
    ) -> ToolResult:
        """Execute scraping with retry logic."""
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ToolResult(success=False, output="", error=f"Invalid URL: {url}")

        # Fetch page
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FreyaBot/1.0; +https://github.com/MrPink1977/freya_project)"
        }
        response = requests.get(url, headers=headers, timeout=10)
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

            output = "\n".join(links[:50])  # Limit to 50 links
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
                # Get text and clean it up
                text = main_content.get_text(separator="\n", strip=True)
                # Remove excessive whitespace
                text = re.sub(r"\n\s*\n", "\n\n", text)
                text = re.sub(r" +", " ", text)
                output = text.strip()
            else:
                output = "Could not extract main content"

        # Truncate if needed
        if len(output) > max_length:
            output = output[:max_length] + f"... (truncated from {len(output)} chars)"

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "url": url,
                "mode": mode,
                "length": len(output),
                "title": soup.find("title").get_text().strip() if soup.find("title") else None,
            },
        )


__all__ = ["WebScraperTool"]
