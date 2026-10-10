"""Root-level smoke validation for the supported install flow and entry point."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_main_is_importable():
    import main

    assert callable(main.main)


def test_main_starts():
    result = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--version"],
        capture_output=True, text=True, timeout=60, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "GhostGoat" in result.stdout


def test_console_script_target_is_main():
    text = (ROOT / "pyproject.toml").read_text()
    assert 'nexus = "main:main"' in text
