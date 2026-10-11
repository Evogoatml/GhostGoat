"""Deprecated import path for the supported FastAPI application.

Use ``main.py`` to start the supported runtime. This module only re-exports
that application's ASGI object; it does not provide a separate orchestrator.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.api.server import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8420)
