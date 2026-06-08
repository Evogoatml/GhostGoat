#!/usr/bin/env python3
"""
Public API Connector.
Fetches and caches public API data from multiple sources.
"""
from __future__ import annotations

import os
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Any


class PublicAPIConfig:
    """Configuration for public API connector."""
    api_url: str = "https://api.publicapis.org/entries"
    cache_path: str = ""
    log_level: str = "INFO"


def load_config(base_dir: str = "") -> PublicAPIConfig:
    """Load configuration."""
    config = PublicAPIConfig()
    base = base_dir or os.path.dirname(os.path.dirname(__file__))
    config.cache_path = os.path.join(base, "data", "public_api_cache.json")
    return config


def setup_logging(config: PublicAPIConfig) -> logging.Logger:
    """Setup logging."""
    logger = logging.getLogger("public_api_connector")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.log_level))
    return logger


def fetch_api_list(
    force: bool = False,
    config: Optional[PublicAPIConfig] = None,
    logger: Optional[logging.Logger] = None
) -> dict[str, Any]:
    """Fetch live data, else fallback to cache."""
    config = config or load_config()
    logger = logger or setup_logging(config)
    
    cache_path = Path(config.cache_path)
    os.makedirs(cache_path.parent, exist_ok=True)
    
    if not force and cache_path.exists():
        try:
            with cache_path.open() as f:
                cache = json.load(f)
                if cache and "entries" in cache:
                    logger.info(f"[CACHE] Loaded {len(cache['entries'])} cached APIs.")
                    return cache
        except Exception as e:
            logger.warning(f"[WARN] Cache load failed: {e}")
    
    # Try imports - gracefully handle if modules not available
    try:
        from modules.data_bridge import get_live_data
        data = get_live_data(config.api_url)
    except ImportError:
        logger.warning("[NET] data_bridge module not available")
        data = {"error": "module not available"}
    
    if "error" in data or not data:
        logger.info("[NET] API feed unavailable, using cache")
        if cache_path.exists():
            with cache_path.open() as f:
                return json.load(f)
        return {"entries": []}
    
    with cache_path.open("w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"[NET] Live data: {len(data.get('entries', []))} records")
    return data


def search_api(
    keyword: str,
    config: Optional[PublicAPIConfig] = None,
    logger: Optional[logging.Logger] = None
) -> list[dict]:
    """Search for APIs containing the keyword."""
    config = config or load_config()
    logger = logger or setup_logging(config)
    
    data = fetch_api_list(config=config, logger=logger)
    results = [
        entry for entry in data.get("entries", [])
        if keyword.lower() in entry.get("API", "").lower()
    ]
    
    if results:
        logger.info(f"[MATCH] Found {len(results)} APIs containing '{keyword}'")
    else:
        logger.info(f"[INFO] No results for '{keyword}'")
    
    return results


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Public API Connector")
    parser.add_argument("keyword", nargs="?", default="security", help="Search keyword")
    parser.add_argument("--force", action="store_true", help="Force fresh fetch")
    
    args = parser.parse_args()
    
    config = load_config()
    logger = setup_logging(config)
    
    results = search_api(args.keyword, config, logger)
    
    for r in results[:10]:
        print(f"  {r.get('API', 'unknown')}")


if __name__ == "__main__":
    main()