"""
Web search tools.

Relocated from empire/superagi's DuckDuckGoSearchTool + SearxSearchTool.
Stripped of ORM dependencies, works standalone.
"""

import logging
from typing import Any, Dict, Optional

from frameworks.agents.tools import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class DuckDuckGoSearchTool(BaseTool):
    """Search the web using DuckDuckGo and optionally scrape + summarize results.

    Requires: pip install duckduckgo-search
    Optional: beautifulsoup4 for page scraping
    """

    name = "duckduckgo_search"
    description = "Search the web using DuckDuckGo. Returns search results with titles, URLs, and snippets."

    def __init__(self, max_results: int = 5, scrape_pages: bool = False,
                 config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self.max_results = max_results
        self.scrape_pages = scrape_pages

    def _execute(self, query: str, **kwargs) -> ToolResult:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return ToolResult(
                output="duckduckgo-search not installed. Run: pip install duckduckgo-search",
                success=False,
            )

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=self.max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

        if not results:
            return ToolResult(output="No results found.", metadata={"query": query})

        if self.scrape_pages:
            return self._scrape_and_format(results, query)

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n   {r['url']}\n   {r['snippet']}")
        return ToolResult(
            output="\n\n".join(lines),
            metadata={"query": query, "result_count": len(results)},
        )

    def _scrape_and_format(self, results, query: str) -> ToolResult:
        """Scrape top result pages and return their text content."""
        try:
            from frameworks.agents.tools.web_scraper import WebScraperTool
        except ImportError:
            # Fall back to snippet-only output
            lines = [f"{r['title']}: {r['snippet']}" for r in results]
            return ToolResult(output="\n\n".join(lines), metadata={"query": query})

        scraper = WebScraperTool()
        scraped = []
        for r in results[:3]:
            page = scraper.execute(r["url"])
            if page.success:
                scraped.append(f"## {r['title']}\n{page.output[:2000]}")

        return ToolResult(
            output="\n\n---\n\n".join(scraped) if scraped else "Could not scrape any pages.",
            metadata={"query": query, "pages_scraped": len(scraped)},
        )

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }
