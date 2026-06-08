"""
CodeBridge — safe code execution and generation for agents.
Execution runs in a subprocess sandbox with timeout.
Generation uses the LLMController.
"""
from __future__ import annotations
import logging
import subprocess
import sys
import tempfile
import os
from typing import Dict

logger = logging.getLogger(__name__)

_TIMEOUT = 15  # seconds


class CodeBridge:

    # ── execution ─────────────────────────────────────────────────────────────

    def run_python(self, code: str, timeout: int = _TIMEOUT) -> Dict:
        """Execute Python code in an isolated subprocess. Returns {stdout, stderr, ok}."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            path = f.name
        try:
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True, text=True, timeout=timeout,
            )
            return {
                "ok": proc.returncode == 0,
                "stdout": proc.stdout[:4000],
                "stderr": proc.stderr[:2000],
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": f"Timeout after {timeout}s", "returncode": -1}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def run_shell(self, command: str, timeout: int = _TIMEOUT) -> Dict:
        """Execute a shell command. Returns {stdout, stderr, ok}."""
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=timeout,
            )
            return {
                "ok": proc.returncode == 0,
                "stdout": proc.stdout[:4000],
                "stderr": proc.stderr[:2000],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e)}

    # ── generation ────────────────────────────────────────────────────────────

    def generate(self, description: str, language: str = "python") -> str:
        """Ask the LLM to write code for a description."""
        from core.controllers.llm_controller import llm
        prompt = (
            f"Write {language} code to: {description}\n\n"
            "Return ONLY the code, no explanation, no markdown fences."
        )
        return llm.call(prompt)

    def generate_and_run(self, description: str) -> Dict:
        """Generate Python code then immediately execute it."""
        code = self.generate(description, language="python")
        result = self.run_python(code)
        result["code"] = code
        return result


code_bridge = CodeBridge()
