
import requests, json

def fetch(url, headers=None):
    try:
        resp = requests.get(url, headers=headers or {}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print("⚠ Error:", resp.status_code)
    except Exception as e:
        print("Network error:", e)
    return None
