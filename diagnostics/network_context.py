# modules/diagnostics/network_context.py
import socket, requests

def internet_available(host="8.8.8.8", port=53, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

def can_use_api():
    """Check if APIs should be allowed this session."""
    # Example: only allow if explicitly enabled or network is stable
    online = internet_available()
    try:
        ping = requests.get("https://api.apilayer.com", timeout=3).status_code
        api_online = ping in [200, 403]  # both mean reachable
    except Exception:
        api_online = False

    if online and api_online:
        print("[NET] API access available ✅")
        return True
    else:
        print("[NET] API use disabled (offline mode) 🚫")
        return False
