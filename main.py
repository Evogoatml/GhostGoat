#!/usr/bin/env python3
"""GhostGoat full runtime: the single startup entry point.

One process boots the orchestrator, then serves the REST API, the Telegram
service and the dashboard from that same orchestrator instance.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Load .env file from project root
from dotenv import load_dotenv
load_dotenv()

ROOT = Path(__file__).parent.absolute()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / 'ghostgoat.log')
    ]
)
logger = logging.getLogger("ghostgoat.main")


async def start_dashboard(port: int) -> asyncio.subprocess.Process:
    """Start the dashboard inside the runtime loop."""
    dashboard_dir = ROOT / "dashboard"
    try:
        return await _launch_dashboard(dashboard_dir, port)
    except FileNotFoundError as exc:
        raise RuntimeError("Node.js 18+ (npm/npx) is required to start the dashboard") from exc


async def _launch_dashboard(dashboard_dir: Path, port: int) -> asyncio.subprocess.Process:
    if not (dashboard_dir / "node_modules").exists():
        logger.info("Installing dashboard dependencies...")
        install = await asyncio.create_subprocess_exec("npm", "install", cwd=dashboard_dir)
        if await install.wait() != 0:
            raise RuntimeError("npm install failed for the dashboard")
    logger.info("Starting dashboard on port %d", port)
    return await asyncio.create_subprocess_exec(
        "npx", "vite", "--port", str(port), cwd=dashboard_dir
    )


async def run() -> None:
    import uvicorn

    from config.api.server import app
    from run_cognitive_system import get_orchestrator

    orchestrator = get_orchestrator()
    runtime = orchestrator.config.runtime
    dashboard = await start_dashboard(runtime.dashboard_port)
    server = uvicorn.Server(uvicorn.Config(
        app, host=runtime.host, port=runtime.port, log_level="info"))
    logger.info("API: http://%s:%d  Dashboard: http://localhost:%d",
                runtime.host, runtime.port, runtime.dashboard_port)
    async def watch_dashboard():
        code = await dashboard.wait()
        logger.error("Dashboard exited with code %s; stopping runtime", code)
        server.should_exit = True

    watcher = asyncio.create_task(watch_dashboard())
    try:
        await server.serve()
    finally:
        watcher.cancel()
        if dashboard.returncode is None:
            dashboard.terminate()
            await dashboard.wait()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="GhostGoat - Autonomous Multi-Agent Orchestration Platform")
    parser.add_argument("--version", action="version", version="GhostGoat 2.0.0")
    parser.parse_args()

    logger.info("GhostGoat - full runtime (orchestrator, API, Telegram, dashboard)")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    logger.info("GhostGoat stopped")


if __name__ == "__main__":
    main()
