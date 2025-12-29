import requests
import os

PLUGINS_DIR = "../plugins"

def download_plugin(url, name=None):
    """
    Downloads a Python plugin from a remote URL and saves to plugins/.
    """
    if not url.endswith(".py"):
        raise ValueError("Only Python source files allowed.")
    fname = name or url.split("/")[-1]
    dest = os.path.join(PLUGINS_DIR, fname)
    print(f"Downloading {url} -> {dest}")
    resp = requests.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch: {resp.status_code}")
    with open(dest, "w") as f:
        f.write(resp.text)
    print(f"[OK] Plugin saved as {dest}")
    return dest

# Example: download_plugin("https://raw.githubusercontent.com/user/repo/main/myplugin.py")

if __name__ == "__main__":
    url = input("Enter plugin .py URL: ")
    download_plugin(url)
