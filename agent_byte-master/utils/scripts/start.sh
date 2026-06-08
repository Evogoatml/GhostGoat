#!/bin/bash
# =============================================================================
# GhostGoat - Local (non-Docker) Unified Startup
# Runs smoke tests, then starts the orchestrator API gateway.
# For Docker startup use: make start
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

GHOSTGOAT_ENV="${GHOSTGOAT_ENV:-development}"

# ---------------------------------------------------------------------------
# Detect Python
# ---------------------------------------------------------------------------
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "Python not found. Install Python 3.8+"
    exit 1
fi

echo "============================================================"
echo "  GhostGoat Orchestrator — local / ${GHOSTGOAT_ENV}"
echo "============================================================"
echo ""
echo "  Python:  $($PY --version 2>&1)"
echo "  LLM:     ${LLM_PROVIDER:-mock}"
echo "  Memory:  ${MEMORY_BACKEND:-memory}"
echo ""

# ---------------------------------------------------------------------------
# Set defaults
# ---------------------------------------------------------------------------
export LLM_PROVIDER="${LLM_PROVIDER:-mock}"
export MEMORY_BACKEND="${MEMORY_BACKEND:-memory}"

# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------
echo "Running smoke tests ..."
$PY tests/smoke_test.py || {
    echo ""
    echo "Smoke tests failed — aborting."
    exit 1
}

# ---------------------------------------------------------------------------
# Start orchestrator
# ---------------------------------------------------------------------------
echo ""
echo "Starting unified API gateway on port ${API_PORT:-8000} ..."
exec $PY frameworks/api/unified_api_gateway.py "$@"
