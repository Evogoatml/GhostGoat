import asyncio
import json
import os
import subprocess
from pathlib import Path
from duckduckgo_search import DDGS

from ACS_SYSTEM.asi.training_bridge import TrainingBridge

_training_bridge = TrainingBridge()


class ToolRegistry:
    def __init__(self):
        self.tools = {
            "shell": self.shell,
            "web_search": self.web_search,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_training": self.list_training,
            "train": self.train,
            "search_training": self.search_training,
        }

    def get(self, name: str):
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name]

    async def shell(self, cmd: str, **kwargs):
        # Guardrails
        forbidden = ["rm -rf", ":(){:|:&};:"]
        if any(bad in cmd for bad in forbidden):
            return "Denied by policy."
        try:
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=45)
            return (out.stdout + out.stderr)[-4000:]
        except Exception as e:
            return f"Shell error: {e}"

    async def web_search(self, q: str, max_results: int = 5, **kwargs):
        try:
            with DDGS() as ddgs:
                return [r for r in ddgs.text(q, max_results=max_results)]
        except Exception as e:
            return f"Search error: {e}"

    async def read_file(self, path: str, **kwargs):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()[:8000]
        except Exception as e:
            return f"Read error: {e}"

    async def write_file(self, path: str, content: str, **kwargs):
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Write error: {e}"

    async def list_training(self, task: str = None, **kwargs):
        """List available training algorithms, optionally filtered by task."""
        algos = _training_bridge.list_algorithms(task=task)
        return json.dumps(algos, indent=2)

    async def train(self, algorithm: str, **kwargs):
        """Run a training algorithm by name."""
        result = _training_bridge.run_training(algorithm, **kwargs)
        serializable = {k: str(v) for k, v in result.items()}
        return json.dumps(serializable, indent=2)

    async def search_training(self, directory: str = None, **kwargs):
        """Scan for training-related files in the ML directories."""
        files = _training_bridge.scan_training_files(directory=directory)
        return json.dumps(files[:30], indent=2)
