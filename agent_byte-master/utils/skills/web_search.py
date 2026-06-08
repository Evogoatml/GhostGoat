"""
GhostGoat Web Search & Link Processing Service
Fetches, parses, and extracts content from URLs for the orchestrator.

Capabilities:
  - Fetch and extract text/markdown from any URL
  - Extract links, metadata, and structured content
  - Async-first for non-blocking operation in the orchestrator
  - Content caching to avoid re-fetching the same URL
  - URL detection in user messages

Architecture note:
  This is a separated service — it has no dependency on the orchestrator
  or memory systems.  The orchestrator calls it when it detects URLs in
  user input.  Proper separation means this can run independently and
  doesn't add latency to non-URL requests.
"""

import asyncio
import hashlib
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# URL pattern for detecting links in user messages
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\')\]]+|'
    r'www\.[^\s<>"\')\]]+',
    re.IGNORECASE,
)


def extract_urls(text: str) -> List[str]:
    """Extract all URLs from a text string."""
    urls = URL_PATTERN.findall(text)
    # Normalize www. prefixed URLs
    return [u if u.startswith("http") else f"https://{u}" for u in urls]


class WebSearchService:
    """Fetches and processes web content with caching.

    The service tries multiple HTTP libraries in order of preference:
    httpx (async-native) > requests (sync, run in executor) > urllib (stdlib).
    """

    def __init__(self, cache_ttl_s: float = 300.0, max_cache: int = 64):
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl = cache_ttl_s
        self._max_cache = max_cache
        self._lock = threading.Lock()

    def _cache_get(self, url: str) -> Optional[Dict[str, Any]]:
        key = hashlib.md5(url.encode()).hexdigest()
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            ts, data = entry
            if time.time() - ts > self._cache_ttl:
                del self._cache[key]
                return None
            return data

    def _cache_put(self, url: str, data: Dict[str, Any]):
        key = hashlib.md5(url.encode()).hexdigest()
        with self._lock:
            self._cache[key] = (time.time(), data)
            # Evict oldest if over limit
            if len(self._cache) > self._max_cache:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
                del self._cache[oldest_key]

    def fetch_sync(self, url: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Synchronously fetch URL content.

        Returns dict with: url, status, title, text, content_type, links, error
        """
        cached = self._cache_get(url)
        if cached is not None:
            logger.debug("Web cache hit: %s", url)
            return cached

        result: Dict[str, Any] = {
            "url": url,
            "status": None,
            "title": "",
            "text": "",
            "content_type": "",
            "links": [],
            "error": None,
        }

        try:
            # Try httpx first (best HTML handling)
            try:
                import httpx
                resp = httpx.get(url, timeout=timeout, follow_redirects=True)
                result["status"] = resp.status_code
                result["content_type"] = resp.headers.get("content-type", "")
                raw_html = resp.text
            except ImportError:
                # Fall back to requests
                try:
                    import requests as req
                    resp = req.get(url, timeout=timeout, allow_redirects=True)
                    result["status"] = resp.status_code
                    result["content_type"] = resp.headers.get("content-type", "")
                    raw_html = resp.text
                except ImportError:
                    # Stdlib fallback
                    import urllib.request
                    with urllib.request.urlopen(url, timeout=timeout) as resp:
                        result["status"] = resp.status
                        result["content_type"] = resp.headers.get("content-type", "")
                        raw_html = resp.read().decode("utf-8", errors="replace")

            # Extract text content
            result["text"] = self._html_to_text(raw_html)
            result["title"] = self._extract_title(raw_html)
            result["links"] = self._extract_links(raw_html, url)

        except Exception as e:
            result["error"] = str(e)
            logger.warning("Failed to fetch %s: %s", url, e)

        self._cache_put(url, result)
        return result

    async def fetch(self, url: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Async fetch — runs sync fetch in executor to avoid blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_sync, url, timeout)

    async def fetch_many(self, urls: List[str], timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Fetch multiple URLs concurrently."""
        tasks = [self.fetch(url, timeout) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def search_content(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Search across fetched content for relevant sections."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored = []

        for result in results:
            if result.get("error"):
                continue
            text = result.get("text", "").lower()
            # Simple relevance scoring
            score = sum(1 for w in query_words if w in text)
            if score > 0:
                # Extract relevant snippet
                snippet = self._extract_snippet(result.get("text", ""), query, max_len=500)
                scored.append({
                    "url": result["url"],
                    "title": result.get("title", ""),
                    "score": score,
                    "snippet": snippet,
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML to readable text."""
        # Try markdownify first (best quality)
        try:
            from markdownify import markdownify as md
            return md(html, strip=["img", "script", "style"])
        except ImportError:
            pass

        # Try BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            pass

        # Regex fallback
        text = re.sub(r'<script\b[^>]*>.*?</script\b[^>]*>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _extract_title(html: str) -> str:
        """Extract page title from HTML."""
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_links(html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract links from HTML."""
        links = []
        parsed_base = urlparse(base_url)

        for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL):
            href = match.group(1).strip()
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

            # Resolve relative URLs
            if href.startswith("/"):
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif not href.startswith("http"):
                continue

            if text and len(text) < 200:
                links.append({"url": href, "text": text})

        return links[:50]  # Limit to prevent bloat

    @staticmethod
    def _extract_snippet(text: str, query: str, max_len: int = 500) -> str:
        """Extract a relevant snippet around query terms."""
        query_words = query.lower().split()
        text_lower = text.lower()

        best_pos = 0
        for word in query_words:
            pos = text_lower.find(word)
            if pos >= 0:
                best_pos = pos
                break

        start = max(0, best_pos - max_len // 4)
        end = min(len(text), start + max_len)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet


# Module-level singleton
_web_service: Optional[WebSearchService] = None


def get_web_service() -> WebSearchService:
    """Get or create the web search service singleton."""
    global _web_service
    if _web_service is None:
        _web_service = WebSearchService()
    return _web_service
