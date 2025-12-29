#!/usr/bin/env python3
# modules/public_api_connector.py

import os, sys, json

# --- Fix path so it works no matter where you run it ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_bridge import get_live_data
from modules.api_keys import get_apilayer_key

API_KEY = get_apilayer_key()
API_URL = "https://api.publicapis.org/entries"
CACHE_PATH = os.path.expanduser("~/adaptive_vault/data/public_api_cache.json")
APILAYER_URL = f"https://api.apilayer.com/ip_to_location/134.201.250.155?apikey={API_KEY}"

def fetch_api_list(force=False):
    """Fetch live data, else fallback to cache."""
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    if not force and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f:
                cache = json.load(f)
                if cache and "entries" in cache:
                    print(f"[CACHE] Loaded {len(cache['entries'])} cached APIs.")
                    return cache
        except Exception as e:
            print(f"[WARN] Cache load failed: {e}")

    # Try main source
    data = get_live_data(API_URL)
    if "error" in data or not data:
        print("[NET] Public API feed unavailable. Trying Apilayer...")
        alt = get_live_data(APILAYER_URL)
        if "error" not in alt and alt:
            print("[NET] Apilayer data retrieved successfully.")
            data = {"entries": [{"API": "Apilayer IP Lookup", "Link": APILAYER_URL, "Data": alt}]}
        else:
            print("[NET] Both sources offline; fallback to cache.")
            if os.path.exists(CACHE_PATH):
                with open(CACHE_PATH, "r") as f:
                    return json.load(f)
            return {"entries": []}

    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[NET] Live data acquired: {len(data.get('entries', []))} records")
    return data

def search_api(keyword):
    """Search for APIs containing the keyword."""
    data = fetch_api_list()
    results = [
        entry for entry in data.get("entries", [])
        if keyword.lower() in entry.get("API", "").lower()
    ]
    if results:
        print(f"[MATCH] Found {len(results)} APIs containing '{keyword}'")
        for r in results[:10]:
            print(f"🔗 {r['API']} — {r.get('Link', 'no link')}")
    else:
        print(f"[INFO] No results for '{keyword}'")
    return results

if __name__ == "__main__":
    search_api("security")
