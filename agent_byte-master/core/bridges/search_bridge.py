"""
SearchBridge — unified web search across multiple providers.
Tries: DuckDuckGo → Google (via SerpAPI) → Bing → fallback scrape.
"""
from __future__ import annotations
import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)


class SearchBridge:

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search and return list of {title, url, snippet}."""
        for method in [self._duckduckgo, self._serpapi, self._basic_scrape]:
            try:
                results = method(query, num_results)
                if results:
                    logger.info("[Search] '%s' via %s → %d results", query[:40], method.__name__, len(results))
                    return results
            except Exception as e:
                logger.debug("[Search] %s failed: %s", method.__name__, e)
        return []

    def search_text(self, query: str, num_results: int = 5) -> str:
        """Return search results as plain text for LLM consumption."""
        results = self.search(query, num_results)
        if not results:
            return f"No results found for: {query}"
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title','')}\n   {r.get('url','')}\n   {r.get('snippet','')}")
        return "\n\n".join(lines)

    def _duckduckgo(self, query: str, n: int) -> List[Dict]:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return [
                {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                for r in ddgs.text(query, max_results=n)
            ]

    def _serpapi(self, query: str, n: int) -> List[Dict]:
        import requests
        key = os.getenv("SERPAPI_KEY", "")
        if not key:
            raise RuntimeError("No SERPAPI_KEY")
        resp = requests.get("https://serpapi.com/search", params={
            "q": query, "api_key": key, "num": n, "engine": "google"
        }, timeout=10)
        items = resp.json().get("organic_results", [])
        return [{"title": r.get("title",""), "url": r.get("link",""),
                 "snippet": r.get("snippet","")} for r in items[:n]]

    def _basic_scrape(self, query: str, n: int) -> List[Dict]:
        import urllib.request, urllib.parse, re
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', html)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</span>', html)
        results = []
        for t, s in zip(titles[:n], snippets[:n]):
            results.append({"title": re.sub(r"<[^>]+>", "", t).strip(),
                             "url": "", "snippet": re.sub(r"<[^>]+>", "", s).strip()})
        return results


search_bridge = SearchBridge()
