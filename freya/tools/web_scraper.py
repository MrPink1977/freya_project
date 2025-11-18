"""Web scraping tools for Freya."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

try:
    import requests  # type: ignore[import-untyped]
except ImportError:
    requests = None  # type: ignore[assignment]

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]

from .base import FreyaTool, ToolResult


class WebScraperTool(FreyaTool):
    """Scrape and extract content from web pages."""

    @property
    def name(self) -> str:
        return "web_scraper"

    @property
    def description(self) -> str:
        return "Scrape and extract text content, links, or specific elements from web pages"

    def execute(  # type: ignore[override]
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
                success=False, output="", error="requests library not installed. Run: pip install requests"
            )

        if BeautifulSoup is None:
            return ToolResult(
                success=False, output="", error="beautifulsoup4 library not installed. Run: pip install beautifulsoup4"
            )

        try:
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
                    # href could be a string or list; normalize to string
                    href_str = href[0] if isinstance(href, list) else str(href)
                    text = link.get_text().strip()
                    full_url = urljoin(url, href_str)
                    if text and href_str:
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

            title_tag = soup.find("title")
            title_text = title_tag.get_text().strip() if title_tag else None

            return ToolResult(
                success=True,
                output=output,
                metadata={"url": url, "mode": mode, "length": len(output), "title": title_text},
            )

        except requests.Timeout:
            return ToolResult(success=False, output="", error=f"Request timeout for {url}")
        except requests.RequestException as e:
            return ToolResult(success=False, output="", error=f"Failed to fetch URL: {e}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Scraping failed: {e}")


__all__ = ["WebScraperTool"]
