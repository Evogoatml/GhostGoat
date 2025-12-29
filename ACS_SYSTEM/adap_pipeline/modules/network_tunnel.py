#!/usr/bin/env python3
# modules/network_tunnel.py

import os
from pyngrok import ngrok

TOKEN_FILE = os.path.expanduser("~/adaptive_vault/keys/ngrok_token.txt")
ACTIVE_TUNNELS = {}

def get_token():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError("Ngrok token not configured.")
    with open(TOKEN_FILE) as f:
        return f.read().strip()

def activate_tunnel(port=8000, proto="http"):
    """Activate an ngrok tunnel only when needed."""
    if port in ACTIVE_TUNNELS:
        return ACTIVE_TUNNELS[port]
    token = get_token()
    os.environ["NGROK_AUTHTOKEN"] = token
    tunnel = ngrok.connect(addr=port, proto=proto)
    public_url = tunnel.public_url
    ACTIVE_TUNNELS[port] = public_url
    print(f"[NET] Ngrok tunnel active on port {port} → {public_url}")
    return public_url

def deactivate_tunnel(port=None):
    """Close one or all tunnels."""
    if port and port in ACTIVE_TUNNELS:
        ngrok.disconnect(ACTIVE_TUNNELS[port])
        print(f"[NET] Tunnel on port {port} closed.")
        del ACTIVE_TUNNELS[port]
    else:
        ngrok.kill()
        ACTIVE_TUNNELS.clear()
        print("[NET] All tunnels closed.")

def check_tunnels():
    """Return dict of active tunnels."""
    return ACTIVE_TUNNELS
