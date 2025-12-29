#!/usr/bin/env python3
# modules/public_api_connector.py

import os, sys, json, requests

# --- Fix path so it works no matter where you run it ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_KEY = "AUdPN6iRpDy8DUR4OjbMTSdxIoDtOBLh"
API_URL = "https://api.apilayer.com/exchangerates_data/latest?base=USD"
CACHE_PATH = os.path.expanduser("~/adaptive_vault/data/public_api_cache.json")


def fetch_api_list(force=False):
    """Fetch live exchange rate data, else fallback to cache."""
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    if not force and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r") as f:
                cache = json.load(f)
                if cache and "rates" in cache:
                    print(f"[CACHE] Loaded {len(cache['rates'])} cached currency pairs.")
                    return cache
        except Exception as e:
            print(f"[WARN] Cache load failed: {e}")

    try:
        headers = {"apikey": API_KEY}
        resp = requests.get(API_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            with open(CACHE_PATH, "w") as f:
                json.dump(data, f, indent=2)
            print(f"[NET] Live data acquired: {len(data.get('rates', {}))} currency rates.")
            return data
        else:
            print(f"[NET] Failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"[ERROR] Network error: {e}")

    print("[NET] Fallback to cache.")
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {"rates": {}}


def search_api(keyword):
    """Search for currencies containing the keyword."""
    data = fetch_api_list()
    rates = data.get("rates", {})
    matches = {k: v for k, v in rates.items() if keyword.lower() in k.lower()}
    if matches:
        print(f"[MATCH] Found {len(matches)} currencies matching '{keyword}':")
        for k, v in list(matches.items())[:10]:
            print(f"💱 {k}: {v}")
    else:
        print(f"[INFO] No currency match for '{keyword}'")
    return matches


if __name__ == "__main__":
    search_api("usd")
