from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({
        "status": "Adaptive Vault is live",
        "environment": os.getenv("HF_SPACE_ID", "local")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
