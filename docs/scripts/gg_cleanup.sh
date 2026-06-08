#!/usr/bin/env bash
# GhostGoat FULL structural cleanup
# Run from: /home/popic/GhostGoat
# Nothing deleted. Everything moved to /home/popic/_MOVED/<timestamp>/

set -euo pipefail

ROOT="/home/popic/GhostGoat"
TS="$(date +%Y%m%d_%H%M%S)"
MOVED="/home/popic/_MOVED/${TS}"

mv_safe() {
    local src="$1" dest="$2"
    [ -e "$src" ] || { echo "[skip]  $src (not found)"; return; }
    mkdir -p "$(dirname "$dest")"
    mv "$src" "$dest"
    echo "[moved] $src"
    echo "     →  $dest"
}

echo "========================================"
echo " GhostGoat FULL cleanup — $TS"
echo " MOVED bucket: $MOVED"
echo "========================================"

# ─── 1. ROOT DOCKER VARIANTS ─────────────────────────────────────────────────
echo ""
echo "--- 1. Docker variants ---"
for f in Dockerfile.backup Dockerfile.orig Dockerfile.orig.backup Dockerfile.fixed Dockerfile.test docker-compose.yml.bak; do
    mv_safe "$ROOT/$f" "$MOVED/docker_variants/$f"
done

# ─── 2. ROOT LOGS → logs/ ────────────────────────────────────────────────────
echo ""
echo "--- 2. Root logs → logs/ ---"
mv_safe "$ROOT/server.log"        "$ROOT/logs/server.log"
mv_safe "$ROOT/server_output.log" "$ROOT/logs/server_output.log"

# ─── 3. STRAY BAK/FIXED FILES ────────────────────────────────────────────────
echo ""
echo "--- 3. .bak/.fixed files ---"
mv_safe "$ROOT/api/orchestrator_api.py.bak"        "$MOVED/bak/orchestrator_api.py.bak"
mv_safe "$ROOT/core/unified_integration.py.fixed"  "$MOVED/bak/unified_integration.py.fixed"

# ─── 4. ROOT NOISE TXT FILES → docs/ ─────────────────────────────────────────
echo ""
echo "--- 4. Noise txt → docs/ ---"
mkdir -p "$ROOT/docs"
for f in GG.txt gg2.txt GGooat.txt; do
    mv_safe "$ROOT/$f" "$ROOT/docs/$f"
done

# ─── 5. RUNTIME STATE → data/runtime/ ────────────────────────────────────────
echo ""
echo "--- 5. Runtime state → data/runtime/ ---"
mkdir -p "$ROOT/data/runtime"
mv_safe "$ROOT/reasoning_history.json" "$ROOT/data/runtime/reasoning_history.json"
mv_safe "$ROOT/registry.db"            "$ROOT/data/runtime/registry.db"
mv_safe "$ROOT/artifact.bin"           "$MOVED/artifacts/artifact.bin"
mv_safe "$ROOT/-path"                  "$MOVED/malformed/-path"
mv_safe "$ROOT/.coverage.json"         "$ROOT/tests/coverage/.coverage.json"

# ─── 6. TEST FILE OUT OF ROOT ────────────────────────────────────────────────
echo ""
echo "--- 6. test_main.py → tests/ ---"
mv_safe "$ROOT/test_main.py" "$ROOT/tests/test_main.py"

# ─── 7. DUPLICATE .backend — root vs core ────────────────────────────────────
# There is BOTH /.backend and /core/.backend — merge into /core/.backend
echo ""
echo "--- 7. Duplicate .backend ---"
if [ -d "$ROOT/.backend" ] && [ -d "$ROOT/core/.backend" ]; then
    # Move root .backend contents into core/.backend, flag conflicts
    find "$ROOT/.backend" -type f | while IFS= read -r f; do
        rel="${f#$ROOT/.backend/}"
        dest="$ROOT/core/.backend/$rel"
        if [ -e "$dest" ]; then
            mv_safe "$f" "$MOVED/backend_conflict/$rel"
        else
            mkdir -p "$(dirname "$dest")"
            mv "$f" "$dest"
            echo "[merged] .backend/$rel → core/.backend/$rel"
        fi
    done
    rmdir --ignore-fail-on-non-empty "$ROOT/.backend/agents" 2>/dev/null || true
    rmdir --ignore-fail-on-non-empty "$ROOT/.backend" 2>/dev/null || true
elif [ -d "$ROOT/.backend" ]; then
    mv_safe "$ROOT/.backend" "$ROOT/core/.backend"
fi

# ─── 8. backend/target (Rust build) OUT ──────────────────────────────────────
echo ""
echo "--- 8. backend/target (Rust build) ---"
mv_safe "$ROOT/backend/target" "$MOVED/rust_build/backend_target"

# ─── 9. ACS_SYSTEM Rust target OUT ───────────────────────────────────────────
echo ""
echo "--- 9. ACS_SYSTEM cipherdsl rust target ---"
RUST_TARGET="$ROOT/ACS_SYSTEM/adap_dia_sys/modules/cipherdsl/out/rust/target"
mv_safe "$RUST_TARGET" "$MOVED/rust_build/cipherdsl_target"

# ─── 10. VENV OUT OF REPO ────────────────────────────────────────────────────
echo ""
echo "--- 10. venv out of repo ---"
VENV="$ROOT/core/brain/agents/congo/FQES/fqes_env"
if [ -d "$VENV" ]; then
    mkdir -p "/home/popic/.venvs"
    mv "$VENV" "/home/popic/.venvs/fqes_env"
    echo "[moved] fqes_env → /home/popic/.venvs/fqes_env"
    echo "[NOTE]  reactivate: source /home/popic/.venvs/fqes_env/bin/activate"
fi

# ─── 11. dashboard/node_modules OUT ──────────────────────────────────────────
# node_modules never belongs in git — move out, reinstall with npm i
echo ""
echo "--- 11. dashboard/node_modules ---"
mv_safe "$ROOT/dashboard/node_modules" "$MOVED/node_modules/dashboard_node_modules"
echo "[NOTE]  restore with: cd $ROOT/dashboard && npm install"

# ─── 12. CHECKPOINTS — flatten test noise ────────────────────────────────────
# Keep: agent-* checkpoints (real agent state)
# Move: clean_test, done_test, exec_test, final_*, smoke_test, task_test, verify_fix, wired_test
echo ""
echo "--- 12. Checkpoint test dirs ---"
for d in clean_test done_test exec_test final_check final_clean final_run final_test smoke_test task_test verify_fix wired_test ghostgoat_agent_byte; do
    mv_safe "$ROOT/checkpoints/$d" "$MOVED/checkpoints/$d"
done

# ─── 13. data/controlflow — belongs in docs or examples, not data ────────────
echo ""
echo "--- 13. data/controlflow → examples/controlflow ---"
mkdir -p "$ROOT/examples"
mv_safe "$ROOT/data/controlflow" "$ROOT/examples/controlflow"

# ─── 14. data/hf_cache — large ML cache, out of repo ────────────────────────
echo ""
echo "--- 14. data/hf_cache → outside repo ---"
mv_safe "$ROOT/data/hf_cache" "/home/popic/.cache/gg_hf_cache"
echo "[NOTE]  set HF_HOME=/home/popic/.cache/gg_hf_cache in .env"

# ─── 15. keys/ — security risk at root, move to security/keys ────────────────
echo ""
echo "--- 15. keys/ → security/keys/ ---"
if [ -d "$ROOT/keys" ] && [ ! -d "$ROOT/security/keys" ]; then
    mv_safe "$ROOT/keys" "$ROOT/security/keys"
elif [ -d "$ROOT/keys" ] && [ -d "$ROOT/security/keys" ]; then
    # Both exist — flag conflict
    mv_safe "$ROOT/keys" "$MOVED/keys_conflict/root_keys"
    echo "[WARN]  security/crypto/keys already exists — check for duplication"
fi

# ─── 16. pipeline/ — check if redundant with core/ ───────────────────────────
# pipeline/ at root is ambiguous — move to core/pipeline unless it has unique content
echo ""
echo "--- 16. pipeline/ → core/pipeline/ ---"
if [ -d "$ROOT/pipeline" ] && [ ! -d "$ROOT/core/pipeline" ]; then
    mv_safe "$ROOT/pipeline" "$ROOT/core/pipeline"
elif [ -d "$ROOT/pipeline" ]; then
    mv_safe "$ROOT/pipeline" "$MOVED/pipeline_conflict/root_pipeline"
fi

# ─── 17. quarantine/ — already named right, just make sure it's gitignored ───
echo ""
echo "--- 17. quarantine/ — stays, adding to .gitignore ---"

# ─── 18. .pytest_cache OUT ───────────────────────────────────────────────────
echo ""
echo "--- 18. .pytest_cache ---"
mv_safe "$ROOT/.pytest_cache" "$MOVED/pytest_cache"

# ─── 19. ALL __pycache__ ─────────────────────────────────────────────────────
echo ""
echo "--- 19. __pycache__ dirs ---"
find "$ROOT" -type d -name "__pycache__" -print0 2>/dev/null | while IFS= read -r -d '' pc; do
    HASH=$(echo "$pc" | md5sum | cut -c1-8)
    mv_safe "$pc" "$MOVED/pycache/$HASH"
done

# ─── 20. UPDATE .gitignore ───────────────────────────────────────────────────
echo ""
echo "--- 20. .gitignore update ---"
GITIGNORE="$ROOT/.gitignore"
add_gi() { grep -qF "$1" "$GITIGNORE" 2>/dev/null || echo "$1" >> "$GITIGNORE"; }

add_gi "__pycache__/"
add_gi "*.pyc"
add_gi "*.pyo"
add_gi "target/"
add_gi "*.rlib"
add_gi "*.rmeta"
add_gi "venv/"
add_gi ".venv/"
add_gi "fqes_env/"
add_gi "node_modules/"
add_gi "*.log"
add_gi "*.bak"
add_gi "*.orig"
add_gi "*.backup"
add_gi "*.fixed"
add_gi "registry.db"
add_gi "reasoning_history.json"
add_gi ".coverage.json"
add_gi "artifact.bin"
add_gi ".pytest_cache/"
add_gi "checkpoints/clean_test"
add_gi "checkpoints/done_test"
add_gi "checkpoints/exec_test"
add_gi "checkpoints/final_*"
add_gi "checkpoints/smoke_test"
add_gi "checkpoints/task_test"
add_gi "checkpoints/verify_fix"
add_gi "checkpoints/wired_test"
add_gi "data/hf_cache/"
add_gi "data/runtime/"
add_gi "quarantine/"

echo "[updated] .gitignore"

echo ""
echo "========================================"
echo " Done. Moved bucket: $MOVED"
echo " Nothing deleted."
echo " Review with: ls $MOVED"
echo "========================================"
