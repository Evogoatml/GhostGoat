#!/usr/bin/env python3
"""
Adaptive Vault Flask Application.
Simple web server for health checks and status.
"""
from __future__ import annotations

import os
import logging
import sys
from flask import Flask, jsonify
from typing import Optional


class VaultConfig:
    """Configuration for Flask app."""
    host: str = "0.0.0.0"
    port: int = 7860
    debug: bool = False


def create_app(config: Optional[VaultConfig] = None) -> Flask:
    """Create and configure Flask app."""
    config = config or VaultConfig()
    app = Flask(__name__)
    
    @app.route("/")
    def index():
        return jsonify({
            "status": "Adaptive Vault is live",
            "environment": os.getenv("HF_SPACE_ID", "local"),
            "version": "1.0.0",
        })
    
    @app.route("/health")
    def health():
        return jsonify({"status": "healthy"})
    
    @app.route("/ready")
    def ready():
        return jsonify({"status": "ready"})
    
    return app


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adaptive Vault Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    
    app = create_app(VaultConfig(host=args.host, port=args.port, debug=args.debug))
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()