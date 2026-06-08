print("GhostGoat assistant starting...")
#!/usr/bin/env python3
"""GhostGoat entry point – launches the orchestrator bot.
A minimal wrapper that ensures the repository root is on sys.path and then
executes `bots.orchestrator_bot.main()` which itself starts the Telegram bot,
API server, dashboard, etc.
"""
import asyncio
import sys
from pathlib import Path

# Add repository root to PYTHONPATH so internal packages resolve correctly.
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from bots.orchestrator_bot import main as orchestrator_main

async def run():
    await orchestrator_main()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n🛑 Assistant stopped.")
