#!/usr/bin/env python3
"""
GhostGoat Main Entry Point
Autonomous multi-agent orchestration platform with self-assembly, self-healing, and post-quantum security.
"""

import argparse
import asyncio
import logging
import os
import sys
import signal
import subprocess
import time
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.absolute()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / 'ghostgoat.log')
    ]
)
logger = logging.getLogger("ghostgoat.main")

# Global variables for subprocesses
api_process = None
dashboard_process = None


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    # Check for Python dependencies
    try:
        import fastapi
        import uvicorn
    except ImportError:
        missing_deps.append("fastapi/uvicorn")
    
    # Check for Node.js (for dashboard)
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_deps.append("nodejs")
    
    if missing_deps:
        logger.warning(f"Missing dependencies: {', '.join(missing_deps)}")
        logger.warning("Some functionality may be limited.")
        return False
    
    return True


def start_api_server():
    """Start the GhostGoat API server."""
    global api_process
    
    logger.info("Starting GhostGoat API server on port 8420...")
    
    # Change to the config/api directory where the server module is
    api_dir = ROOT / "config" / "api"
    
    try:
        api_process = subprocess.Popen([
            sys.executable, "config/api/server.py"
        ], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if api_process.poll() is None:
            logger.info("API server started successfully")
            return True
        else:
            stdout, stderr = api_process.communicate()
            logger.error(f"API server failed to start: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        return False


def start_dashboard():
    """Start the GhostGoat dashboard."""
    global dashboard_process
    
    logger.info("Starting GhostGoat dashboard on port 3000...")
    
    # Change to the dashboard directory
    dashboard_dir = ROOT / "dashboard"
    
    if not dashboard_dir.exists():
        logger.error("Dashboard directory not found")
        return False
    
    try:
        # Check if node_modules exists, if not install dependencies
        node_modules_dir = dashboard_dir / "node_modules"
        if not node_modules_dir.exists():
            logger.info("Installing dashboard dependencies...")
            subprocess.run(["npm", "install"], cwd=dashboard_dir, check=True, capture_output=True)
        
        # Start the dashboard
        dashboard_process = subprocess.Popen([
            "npx", "vite", "--port", "3000"
        ], cwd=dashboard_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it a moment to start
        time.sleep(3)
        
        # Check if process is still running
        if dashboard_process.poll() is None:
            logger.info("Dashboard started successfully")
            return True
        else:
            stdout, stderr = dashboard_process.communicate()
            logger.error(f"Dashboard failed to start: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        return False


def shutdown():
    """Gracefully shutdown all processes."""
    global api_process, dashboard_process
    
    logger.info("Shutting down GhostGoat...")
    
    if dashboard_process and dashboard_process.poll() is None:
        logger.info("Stopping dashboard...")
        dashboard_process.terminate()
        try:
            dashboard_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            dashboard_process.kill()
    
    if api_process and api_process.poll() is None:
        logger.info("Stopping API server...")
        api_process.terminate()
        try:
            api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_process.kill()
    
    logger.info("Shutdown complete")


def run_api_only():
    """Run API server only."""
    logger.info("Starting GhostGoat in API-only mode...")
    
    if not check_dependencies():
        logger.error("Dependency check failed")
        return False
    
    setup_signal_handlers()
    
    if not start_api_server():
        logger.error("Failed to start API server")
        return False
    
    try:
        logger.info("API server running. Press Ctrl+C to stop.")
        # Keep the main process alive
        while True:
            time.sleep(1)
            # Check if API process is still running
            if api_process and api_process.poll() is not None:
                logger.error("API server process died unexpectedly")
                break
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        shutdown()
    
    return True


def run_dashboard_only():
    """Run dashboard only."""
    logger.info("Starting GhostGoat in dashboard-only mode...")
    
    if not check_dependencies():
        logger.error("Dependency check failed")
        return False
    
    setup_signal_handlers()
    
    if not start_dashboard():
        logger.error("Failed to start dashboard")
        return False
    
    try:
        logger.info("Dashboard running. Press Ctrl+C to stop.")
        # Keep the main process alive
        while True:
            time.sleep(1)
            # Check if dashboard process is still running
            if dashboard_process and dashboard_process.poll() is not None:
                logger.error("Dashboard process died unexpectedly")
                break
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        shutdown()
    
    return True


def run_full():
    """Run full GhostGoat system (API + dashboard)."""
    logger.info("Starting GhostGoat in full mode (API + dashboard)...")
    
    if not check_dependencies():
        logger.error("Dependency check failed")
        return False
    
    setup_signal_handlers()
    
    # Start API server first
    if not start_api_server():
        logger.error("Failed to start API server")
        return False
    
    # Start dashboard
    if not start_dashboard():
        logger.error("Failed to start dashboard")
        shutdown()  # Clean up API server if dashboard fails
        return False
    
    try:
        logger.info("GhostGoat is running!")
        logger.info("API Server: http://localhost:8420")
        logger.info("Dashboard: http://localhost:3000")
        logger.info("Press Ctrl+C to stop all services...")
        
        # Keep the main process alive
        while True:
            time.sleep(1)
            # Check if processes are still running
            if api_process and api_process.poll() is not None:
                logger.error("API server process died unexpectedly")
                break
            if dashboard_process and dashboard_process.poll() is not None:
                logger.error("Dashboard process died unexpectedly")
                break
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        shutdown()
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="GhostGoat - Autonomous Multi-Agent Orchestration Platform")
    parser.add_argument("--api-only", action="store_true", help="Run API server only")
    parser.add_argument("--dash-only", action="store_true", help="Run dashboard only")
    parser.add_argument("--version", action="version", version="GhostGoat 1.0.0")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("GhostGoat - Autonomous Multi-Agent Orchestration Platform")
    logger.info("=" * 60)
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working Directory: {ROOT}")
    logger.info("=" * 60)
    
    # Determine run mode
    if args.api_only:
        success = run_api_only()
    elif args.dash_only:
        success = run_dashboard_only()
    else:
        success = run_full()
    
    if not success:
        logger.error("GhostGoat failed to start properly")
        sys.exit(1)
    
    logger.info("GhostGoat stopped")


if __name__ == "__main__":
    main()