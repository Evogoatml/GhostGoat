#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code on the web sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

echo "[GhostGoat] Installing Python dependencies..."
pip install -r requirements-core.txt --quiet --disable-pip-version-check

echo "[GhostGoat] Installing dashboard dependencies..."
if [ -d "dashboard" ] && [ -f "dashboard/package.json" ]; then
  # Skip if node_modules exists and is newer than package.json
  if [ ! -d "dashboard/node_modules" ] || \
     [ "dashboard/package.json" -nt "dashboard/node_modules" ]; then
    npm install --prefix dashboard --silent
  else
    echo "[GhostGoat] Dashboard node_modules up-to-date, skipping."
  fi
fi

echo "[GhostGoat] Setting PYTHONPATH..."
echo "export PYTHONPATH=\"$CLAUDE_PROJECT_DIR\"" >> "$CLAUDE_ENV_FILE"

echo "[GhostGoat] Session ready."
