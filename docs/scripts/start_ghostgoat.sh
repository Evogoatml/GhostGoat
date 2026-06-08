#!/bin/bash

echo "🐐 Starting GhostGoat Multi-Agent System..."
echo ""

cd ~/GhostGoat

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if API keys are set
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-key-here" ]; then
    echo "⚠️  WARNING: OpenAI API key not configured!"
    echo "Edit .env file: nano ~/GhostGoat/.env"
    echo ""
fi

# Create a simple Python launcher
python3 << 'PYTHON'
import sys
import os
import asyncio

# Add paths
sys.path.insert(0, os.getcwd())

print("═══════════════════════════════════════════════════════")
print("🐐 GHOSTGOAT MULTI-AGENT SYSTEM")
print("═══════════════════════════════════════════════════════")
print("")
print("✅ System initialized")
print("📂 Working directory:", os.getcwd())
print("")

# Try to import core modules
try:
    sys.path.insert(0, 'config')
    import unified_config
    print("✅ Configuration loaded")
except Exception as e:
    print(f"⚠️  Config: {e}")

try:
    sys.path.insert(0, 'core/memory')
    import unified_memory
    print("✅ Memory system loaded")
except Exception as e:
    print(f"⚠️  Memory: {e}")

try:
    sys.path.insert(0, 'frameworks/llm')
    import multi_llm
    print("✅ LLM interface loaded")
except Exception as e:
    print(f"⚠️  LLM: {e}")

print("")
print("═══════════════════════════════════════════════════════")
print("🎯 GhostGoat is ready!")
print("")
print("Available commands:")
print("  1. Run tests: cd tests && python smoke_test.py")
print("  2. Start API: python -m uvicorn frameworks.api.orchestrator_api:app --reload")
print("  3. Interactive mode: python -i start_ghostgoat.sh")
print("")
print("Modules available:")
print("  - config.unified_config")
print("  - core.memory.unified_memory")
print("  - frameworks.llm.multi_llm")
print("  - frameworks.monitoring.monitoring")
print("")
print("═══════════════════════════════════════════════════════")
print("")

# Keep alive for interactive mode
import code
vars = globals().copy()
vars.update(locals())
shell = code.InteractiveConsole(vars)
shell.interact(banner="🐐 GhostGoat Interactive Shell (Ctrl+D to exit)")

PYTHON

