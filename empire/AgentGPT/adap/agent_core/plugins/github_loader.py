"""
GitHub plugin loader
@jarviscmd: Download and install a plugin from a GitHub raw URL.
"""

import requests
import os

def run():
    url = input("Paste raw GitHub .py URL: ").strip()
    if not (url.startswith("https://raw.githubusercontent.com") and url.endswith(".py")):
        print("Error: Must be a direct raw GitHub .py URL.")
        return
    name = url.split("/")[-1]
    dest = os.path.join(os.path.dirname(__file__), name)
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            with open(dest, "w") as f:
                f.write(resp.text)
            print(f"[OK] Plugin '{name}' downloaded.")
        else:
            print(f"Failed: HTTP {resp.status_code}")
    except Exception as e:
        print(f"Download error: {e}")
