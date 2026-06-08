import requests, os, json

API_SOURCE = "https://api.publicapis.org/entries"
CACHE_PATH = os.path.expanduser("~/adaptive_vault/data/public_api_cache.json")

def update_cache():
    """Fetch and cache public API registry with safe offline fallback."""
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    try:
        print("[NET] Fetching from remote catalog...")
        r = requests.get(API_SOURCE, timeout=10)
        r.raise_for_status()
        data = r.json()
        with open(CACHE_PATH, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[NET] Cache updated with {len(data.get('entries', []))} APIs.")
        return data
    except Exception as e:
        print(f"[WARN] Network unavailable or DNS error: {e}")
        if os.path.exists(CACHE_PATH):
            print("[CACHE] Loading fallback data...")
            with open(CACHE_PATH) as f:
                return json.load(f)
        print("[CACHE] No cache found, returning empty dataset.")
        return {"entries": []}
