#!/bin/bash
# =============================================================================
# GhostGoat - Docker Entrypoint
# Waits for dependencies, runs initialization, starts the orchestrator.
# =============================================================================
set -e

GHOSTGOAT_ENV="${GHOSTGOAT_ENV:-development}"

# ---------------------------------------------------------------------------
# Dependency readiness checks
# ---------------------------------------------------------------------------
wait_for() {
    local name="$1" host="$2" port="$3" timeout="${4:-30}"
    echo "[entrypoint] Waiting for ${name} (${host}:${port}) ..."
    local elapsed=0
    while ! python -c "import socket; s=socket.create_connection(('${host}', ${port}), 2); s.close()" 2>/dev/null; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ "$elapsed" -ge "$timeout" ]; then
            echo "[entrypoint] WARN: ${name} not reachable after ${timeout}s — continuing anyway"
            return 1
        fi
    done
    echo "[entrypoint] ${name} is ready (${elapsed}s)"
    return 0
}

# Core dependencies
wait_for "Redis"    "${REDIS_HOST:-redis}"       "${REDIS_PORT:-6379}"    30
wait_for "ChromaDB" "${CHROMADB_HOST:-chromadb}"  "${CHROMADB_PORT:-8000}" 30

# Optional dependencies (don't block on these)
if [ -n "$NEO4J_HOST" ]; then
    wait_for "Neo4j" "$NEO4J_HOST" "${NEO4J_PORT:-7687}" 15 || true
fi

# ---------------------------------------------------------------------------
# Smoke tests (dev only — skip in production for fast startup)
# ---------------------------------------------------------------------------
if [ "$GHOSTGOAT_ENV" != "production" ] && [ -f tests/smoke_test.py ]; then
    echo "[entrypoint] Running smoke tests ..."
    python tests/smoke_test.py || {
        echo "[entrypoint] WARN: Smoke tests failed — starting anyway"
    }
fi

# ---------------------------------------------------------------------------
# Start the orchestrator
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo "  GhostGoat Orchestrator — ${GHOSTGOAT_ENV}"
echo "  API:  http://0.0.0.0:${API_PORT:-8000}"
echo "============================================================"
echo ""

exec python frameworks/api/unified_api_gateway.py "$@"
