#!/usr/bin/env bash
# GhostGoat surgical cleanup
# Run from anywhere — hardcoded to /home/popic/GhostGoat
# Nothing deleted. Everything moved to /home/popic/_MOVED/<timestamp>/

set -euo pipefail

ROOT="/home/popic/GhostGoat"
TS="$(date +%Y%m%d_%H%M%S)"
MOVED="/home/popic/_MOVED/${TS}"

mv_safe() {
    local src="$1" dest="$2"
    [ -e "$src" ] || { echo "[skip] $src"; return; }
    mkdir -p "$(dirname "$dest")"
    mv "$src" "$dest"
    echo "[moved] $src  →  $dest"
}

echo "=== GhostGoat cleanup $TS ==="
echo "MOVED bucket: $MOVED"
echo ""

# ─── 1. ROOT BACKUP / VARIANT DOCKERFILES ────────────────────────────────────
# Keep: Dockerfile, docker-compose.yml
# Move out: all .backup .orig .fixed .test variants
for f in \
    Dockerfile.backup \
    Dockerfile.orig \
    Dockerfile.orig.backup \
    Dockerfile.fixed \
    Dockerfile.test \
    docker-compose.yml.bak; do
    mv_safe "$ROOT/$f" "$MOVED/docker_variants/$f"
done

# ─── 2. ROOT LOGS ────────────────────────────────────────────────────────────
# Logs belong in logs/ not root
for f in server.log server_output.log; do
    mv_safe "$ROOT/$f" "$ROOT/logs/$f"
done

# ─── 3. STRAY .bak FILES ─────────────────────────────────────────────────────
mv_safe "$ROOT/api/orchestrator_api.py.bak"   "$MOVED/bak/orchestrator_api.py.bak"
mv_safe "$ROOT/core/unified_integration.py.fixed" "$MOVED/bak/unified_integration.py.fixed"

# ─── 4. STRAY TXT NOISE FILES IN ROOT ────────────────────────────────────────
# GG.txt, gg2.txt, GGooat.txt are notes/tree dumps — move to docs/
mkdir -p "$ROOT/docs"
for f in GG.txt gg2.txt GGooat.txt; do
    mv_safe "$ROOT/$f" "$ROOT/docs/$f"
done

# ─── 5. STALE RUNTIME FILES IN ROOT ─────────────────────────────────────────
# reasoning_history.json and registry.db are runtime state, not source
mkdir -p "$ROOT/data/runtime"
mv_safe "$ROOT/reasoning_history.json" "$ROOT/data/runtime/reasoning_history.json"
mv_safe "$ROOT/registry.db"            "$ROOT/data/runtime/registry.db"

# artifact.bin is a binary artifact, not source
mv_safe "$ROOT/artifact.bin" "$MOVED/artifacts/artifact.bin"

# -path is a malformed file (likely a typo from a find command)
mv_safe "$ROOT/-path" "$MOVED/malformed/-path"

# .coverage.json is test output
mkdir -p "$ROOT/tests/coverage"
mv_safe "$ROOT/.coverage.json" "$ROOT/tests/coverage/.coverage.json"

# ─── 6. TEST FILES OUT OF ROOT ───────────────────────────────────────────────
# test_main.py belongs in tests/
mv_safe "$ROOT/test_main.py" "$ROOT/tests/test_main.py"

# ─── 7. VENV — move outside repo entirely ────────────────────────────────────
VENV="$ROOT/core/brain/agents/congo/FQES/fqes_env"
if [ -d "$VENV" ]; then
    VENV_DEST="/home/popic/.venvs/fqes_env"
    mkdir -p "/home/popic/.venvs"
    mv "$VENV" "$VENV_DEST"
    echo "[moved] venv $VENV  →  $VENV_DEST"
    echo ""
    echo "[NOTE] Reactivate with: source /home/popic/.venvs/fqes_env/bin/activate"
fi

# ─── 8. RUST BUILD TARGET ────────────────────────────────────────────────────
RUST_TARGET="$ROOT/ACS_SYSTEM/adap_dia_sys/modules/cipherdsl/out/rust/target"
if [ -d "$RUST_TARGET" ]; then
    mv_safe "$RUST_TARGET" "$MOVED/rust_build/target"
fi

# ─── 9. ALL __pycache__ DIRS ─────────────────────────────────────────────────
echo ""
echo "=== Clearing __pycache__ ==="
find "$ROOT" -type d -name "__pycache__" -print0 | while IFS= read -r -d '' pc; do
    mv_safe "$pc" "$MOVED/pycache/$(echo "$pc" | md5sum | cut -c1-8)"
done

# ─── 10. ENFORCE .gitignore ──────────────────────────────────────────────────
GITIGNORE="$ROOT/.gitignore"
add_if_missing() {
    grep -qF "$1" "$GITIGNORE" 2>/dev/null || echo "$1" >> "$GITIGNORE"
}
add_if_missing "__pycache__/"
add_if_missing "*.pyc"
add_if_missing "*.pyo"
add_if_missing "target/"
add_if_missing "*.rlib"
add_if_missing "*.rmeta"
add_if_missing "venv/"
add_if_missing ".venv/"
add_if_missing "fqes_env/"
add_if_missing "*.log"
add_if_missing "*.bak"
add_if_missing "*.orig"
add_if_missing "*.backup"
add_if_missing "*.fixed"
add_if_missing "registry.db"
add_if_missing "reasoning_history.json"
add_if_missing ".coverage.json"
add_if_missing "artifact.bin"
echo "[updated] .gitignore"

echo ""
echo "=== Done. Moved bucket: $MOVED ==="
echo "=== Nothing deleted. Run: ls $MOVED ==="
