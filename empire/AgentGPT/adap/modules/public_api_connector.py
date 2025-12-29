
import requests

# Minimal external fetcher used by diagnostics/external_services.
def fetch_api_list(force: bool = False):
    url = "https://api.apilayer.com"  # placeholder reachability check
    try:
        r = requests.get(url, timeout=5)
        return {"status": r.status_code, "ok": r.status_code in (200,403)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
