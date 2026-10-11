#!/bin/bash
# COMPATIBILITY-ONLY: legacy wrapper. The supported install is `pip install -e ".[full]"`
# and the supported entry point is `python main.py`. This script just runs that flow.
set -e

if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Run this from the project root."
    exit 1
fi

pip install -e ".[full]"

echo ""
echo "Install complete. Start GhostGoat with:  python main.py"
