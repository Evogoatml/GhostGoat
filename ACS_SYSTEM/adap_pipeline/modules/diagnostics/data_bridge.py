# modules/data_bridge.py
import requests

def get_live_data(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json() if "application/json" in r.headers.get("Content-Type", "") else r.text
    except Exception as e:
        return {"error": str(e), "source": url}
