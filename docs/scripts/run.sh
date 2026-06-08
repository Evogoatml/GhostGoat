#!/usr/bin/env bash
# GhostGoat — repo reorganization migration script
# Run from the GhostGoat root directory.
# Dry-run by default. Pass --apply to execute.

set -euo pipefail

APPLY=false
[[ "${1:-}" == "--apply" ]] && APPLY=true

run() {
    if $APPLY; then
        echo "  [RUN] $*"
        eval "$@"
    else
        echo "  [DRY] $*"
    fi
}

log() { echo -e "\n\033[1;36m>>> $*\033[0m"; }
warn() { echo -e "  \033[1;33m[WARN]\033[0m $*"; }
ok() { echo -e "  \033[1;32m[OK]\033[0m $*"; }

ROOT="$(pwd)"

# ── Safety check ────────────────────────────────────────────────────────────
if [[ ! -f "$ROOT/main.py" || ! -d "$ROOT/ACS_SYSTEM" ]]; then
    echo "ERROR: Run this from the GhostGoat root (expects main.py and ACS_SYSTEM/)."
    exit 1
fi

if ! $APPLY; then
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║   DRY RUN — no files will be changed         ║"
    echo "║   Pass --apply to execute                    ║"
    echo "╚══════════════════════════════════════════════╝"
fi

# ── Step 1: Create new directory scaffold ───────────────────────────────────
log "Step 1: Creating directory scaffold"
for d in crypto/adap/modules/diagnostics crypto/adap/modules/governance \
          crypto/adap/modules/learning crypto/adap/modules/memory \
          crypto/cipherdsl docker/archive data/db data/logs data/checkpoints \
          asi; do
    run "mkdir -p $d"
done
ok "Scaffold ready"

# ── Step 2: Merge adap_dia_sys + adap_pipeline → crypto/adap/ ───────────────
log "Step 2: Merging ADAP pipelines → crypto/adap/"

# Copy adap_pipeline as the base (has app.py + diag.py)
run "cp -rn ACS_SYSTEM/adap_pipeline/. crypto/adap/"

# Bring unique files from adap_dia_sys (not overwriting)
UNIQUE_DIA=(
    "ACS_SYSTEM/adap_dia_sys/modules/diagnostics/diagnostic_engine.py"
    "ACS_SYSTEM/adap_dia_sys/modules/local_matcher.py"
    "ACS_SYSTEM/adap_dia_sys/modules/performance_profiler.py"
    "ACS_SYSTEM/adap_dia_sys/modules/recommendation_engine.py"
    "ACS_SYSTEM/adap_dia_sys/modules/task_handler.py"
)
for f in "${UNIQUE_DIA[@]}"; do
    dest="crypto/adap/modules/$(basename $f)"
    [[ "$f" == *"diagnostics"* ]] && dest="crypto/adap/modules/diagnostics/$(basename $f)"
    run "cp -n $f $dest"
done

# Fix typo: google_intergration → google_integration in adap
if [[ -f "crypto/adap/modules/google_intergration.py" ]]; then
    run "mv crypto/adap/modules/google_intergration.py crypto/adap/modules/google_integration.py"
fi
ok "ADAP merged into crypto/adap/"

# ── Step 3: Move CipherDSL → crypto/cipherdsl/ ──────────────────────────────
log "Step 3: Moving CipherDSL → crypto/cipherdsl/"
run "cp -rn ACS_SYSTEM/cipherdsl/. crypto/cipherdsl/"
ok "CipherDSL moved"

# Move advanced_ciphers.py
if [[ -f "ACS_SYSTEM/advanced_ciphers.py" ]]; then
    run "cp ACS_SYSTEM/advanced_ciphers.py crypto/advanced_ciphers.py"
    ok "advanced_ciphers.py → crypto/"
fi

# ── Step 4: Move ASI → asi/ ──────────────────────────────────────────────────
log "Step 4: Moving ASI layer → asi/"
run "cp -rn ACS_SYSTEM/asi/. asi/"
ok "ASI moved"

# ── Step 5: Consolidate Dockerfiles → docker/ ───────────────────────────────
log "Step 5: Consolidating Dockerfiles → docker/"
run "cp Dockerfile docker/Dockerfile"
for variant in Dockerfile.backup Dockerfile.fixed Dockerfile.orig \
               Dockerfile.orig.backup Dockerfile.test; do
    [[ -f "$variant" ]] && run "mv $variant docker/archive/$variant"
done
[[ -f "docker-compose.yml.bak" ]] && run "mv docker-compose.yml.bak docker/archive/"
ok "Dockerfiles consolidated"

# ── Step 6: Move runtime state → data/ ──────────────────────────────────────
log "Step 6: Moving runtime state → data/"
DB_FILES=(brain_memory.db brain_optimizer.db registry.db)
for f in "${DB_FILES[@]}"; do
    [[ -f "$f" ]] && run "mv $f data/db/$f"
done

LOG_FILES=(server.log server_output.log build.log critical_errors.log)
for f in "${LOG_FILES[@]}"; do
    [[ -f "$f" ]] && run "mv $f data/logs/$f"
done

[[ -f "reasoning_history.json" ]] && run "mv reasoning_history.json data/"
[[ -d "checkpoints" ]]            && run "mv checkpoints data/checkpoints"
[[ -f "artifact.bin" ]]           && run "mv artifact.bin data/"
ok "Runtime state moved to data/"

# ── Step 7: Fix google_integration typo in integrations/ ────────────────────
log "Step 7: Fixing typo in integrations/"
if [[ -f "integrations/google_intergration.py" ]]; then
    run "mv integrations/google_intergration.py integrations/google_integration.py"
    ok "Typo fixed: google_intergration → google_integration"
fi

# ── Step 8: Delete ACS_SYSTEM (after content moved) ─────────────────────────
log "Step 8: Removing ACS_SYSTEM/ (content migrated)"
warn "Review crypto/, asi/ before deleting — ensure all files landed correctly."
if $APPLY; then
    read -rp "  Delete ACS_SYSTEM/? [y/N] " confirm
    [[ "$confirm" == "y" ]] && rm -rf ACS_SYSTEM/ && ok "ACS_SYSTEM/ deleted"
else
    echo "  [DRY] rm -rf ACS_SYSTEM/   ← requires manual confirm with --apply"
fi

# ── Step 9: Purge __pycache__ everywhere ────────────────────────────────────
log "Step 9: Purging __pycache__ and *.pyc"
run "find . -type d -name '__pycache__' -not -path './venv/*' -exec rm -rf {} + 2>/dev/null || true"
run "find . -name '*.pyc' -not -path './venv/*' -delete 2>/dev/null || true"
ok "__pycache__ purged"

# ── Step 10: SECURITY — keys audit ──────────────────────────────────────────
log "Step 10: Keys audit (MANUAL ACTION REQUIRED)"
warn "PEM files found at:"
find . -name "*.pem" -not -path "./venv/*" 2>/dev/null | while read -r f; do
    warn "  $f"
done
echo ""
echo "  ACTION REQUIRED:"
echo "  1. Rotate all exposed private keys immediately."
echo "  2. Remove keys from git history:"
echo "     pip install git-filter-repo"
echo "     git filter-repo --path keys/ --invert-paths"
echo "     git filter-repo --path-glob '*.pem' --invert-paths"
echo "  3. Store secrets in: env vars, AWS Secrets Manager, or HashiCorp Vault."
echo "  4. Add keys/ and *.pem to .gitignore (already in the new .gitignore)."

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
if $APPLY; then
echo "║   Migration complete.                        ║"
echo "║   Review changes, then: git add -A           ║"
else
echo "║   Dry run complete. No files changed.        ║"
echo "║   Run with --apply to execute.               ║"
fi
echo "╚══════════════════════════════════════════════╝"
