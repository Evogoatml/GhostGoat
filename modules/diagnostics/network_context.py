
import socket, requests

def online():
    try:
        socket.create_connection(("1.1.1.1", 80), 2)
        return True
    except OSError:
        return False

def can_use_api():
    if not online():
        print("🚫 Offline mode.")
        return False
    try:
        r = requests.get("https://api.apilayer.com", timeout=3)
        print("🌐 API access available." if r.status_code < 500 else "⚠ API responded but may be limited.")
        return True
    except Exception:
        print("⚠ Network reachable, but API unreachable.")
        return False
