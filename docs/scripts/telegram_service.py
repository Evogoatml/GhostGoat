#!/usr/bin/env python3
"""
Telegram Bot Service Wrapper for GhostGoat Orchestrator
Launches GhostGoat's integrated telegram interface as a managed service
"""
import os
import subprocess
import sys
from pathlib import Path

def main():
    # Change to the GhostGoat root directory
    ghostgoat_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(ghostgoat_root)
    
    # Ensure we're using the correct Python environment (from venv)
    venv_python = os.path.join(ghostgoat_root, "venv", "bin", "python")
    if os.path.exists(venv_python):
        python_executable = venv_python
    else:
        python_executable = sys.executable
    
    # Run GhostGoat's integrated telegram interface
    telegram_script = os.path.join(ghostgoat_root, "integrations", "telegram_bot.py")
    
    if not os.path.exists(telegram_script):
        print(f"[Telegram Service] ERROR: {telegram_script} not found")
        sys.exit(1)
        
    print(f"[Telegram Service] Starting GhostGoat's integrated telegram interface")
    print(f"[Telegram Service] Working directory: {ghostgoat_root}")
    subprocess.run([python_executable, telegram_script])

if __name__ == "__main__":
    main()