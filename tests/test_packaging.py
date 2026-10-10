"""Guards the single supported install/run path."""
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_is_canonical():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert data["project"]["scripts"]["nexus"] == "main:main"
    assert "full" in data["project"]["optional-dependencies"]


def test_no_stray_requirements_files():
    names = {p.name for p in ROOT.glob("requirements*.txt")}
    assert names <= {"requirements.txt"}


def test_no_tracked_generated_artifacts():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        return
    bad = [f for f in out.stdout.splitlines()
           if "__pycache__/" in f or f.endswith((".pyc", ".pyo")) or ".egg-info/" in f]
    assert not bad
