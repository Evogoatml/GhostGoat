from flask import Flask, jsonify
import threading
import time
import requests
import os

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "status": "✅ Adaptive Vault running",
        "uptime": True,
        "service": os.getenv("RENDER_SERVICE_NAME", "local-dev")
    })

@app.route("/health")
def health():
    return jsonify({"health": "ok", "timestamp": time.time()})

# Background heartbeat that pings Render to keep it awake
def heartbeat():
    while True:
        try:
            url = os.getenv("RENDER_EXTERNAL_URL")
            if url:
                requests.get(f"{url}/health", timeout=5)
        except Exception:
            pass
        time.sleep(240)  # every 4 minutes

def start_heartbeat():
    t = threading.Thread(target=heartbeat, daemon=True)
    t.start()

@app.before_first_request
def _start_heartbeat_once():
    # Ensure heartbeat starts when running under Gunicorn/Render
    start_heartbeat()

if __name__ == "__main__":
    start_heartbeat()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
