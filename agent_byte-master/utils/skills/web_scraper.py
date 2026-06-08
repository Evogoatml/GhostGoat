"""
Web scraper tool.

Relocated from empire/superagi's WebScraperTool.
Extracts readable text from a URL using BeautifulSoup.
"""

import logging
from typing import Any, Dict, Optional

from frameworks.agents.tools import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebScraperTool(BaseTool):
    """Scrape a webpage and extract its text content.

    Requires: pip install beautifulsoup4 requests
    """

    name = "web_scraper"
    description = "Fetch a URL and extract its text content."

    def __init__(self, max_words: int = 600, timeout: int = 10,
                 config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.max_words = max_words
        self.timeout = timeout

    def _execute(self, url: str, **kwargs) -> ToolResult:
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            return ToolResult(
                output="beautifulsoup4 or requests not installed.",
                success=False,
            )

        try:
            resp = requests.get(url, timeout=self.timeout, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GhostGoat/1.0)"
            })
            resp.raise_for_status()
        except Exception as e:
            return ToolResult(output=f"Failed to fetch {url}: {e}", success=False)

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script/style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Truncate to max_words
        words = text.split()
        if len(words) > self.max_words:
            text = " ".join(words[:self.max_words]) + "..."

        return ToolResult(
            output=text,
            metadata={"url": url, "word_count": min(len(words), self.max_words)},
        )

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
            },
            "required": ["url"],
        }
