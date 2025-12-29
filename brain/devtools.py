import os
import subprocess
import tempfile
import traceback
from io import StringIO
from contextlib import redirect_stdout

# Optional imports
try:
    import black
    HAS_BLACK = True
except ImportError:
    HAS_BLACK = False

try:
    import pylint.lint
    HAS_PYLINT = True
except ImportError:
    HAS_PYLINT = False

class DevTools:
    """Agent developer toolkit for linting, refactoring, and testing code."""

    def __init__(self, workspace="."):
        self.workspace = workspace

    # -------------------- CODE FORMAT --------------------
    def format_code(self, code: str) -> str:
        """Use Black to autoformat Python code."""
        if not HAS_BLACK:
            return "[format_code] Error: Black module not installed"
        try:
            return black.format_str(code, mode=black.FileMode())
        except Exception as e:
            return f"[format_code] Error: {e}"

    # -------------------- CODE LINT --------------------
    def lint_code(self, code_path: str) -> str:
        """Run pylint on a file or directory and return the report."""
        if not HAS_PYLINT:
            return "[lint_code] Error: Pylint module not installed"
        try:
            pylint_output = StringIO()
            with redirect_stdout(pylint_output):
                pylint.lint.Run([code_path], exit=False)
            return pylint_output.getvalue()
        except Exception as e:
            return f"[lint_code] Error: {e}"

    # -------------------- CODE TEST --------------------
    def test_snippet(self, code: str) -> str:
        """Run a snippet of Python code safely in isolation."""
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(code)
                tmp_path = f.name
            result = subprocess.run(["python3", tmp_path],
                                    capture_output=True, text=True, timeout=10)
            return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "[test_snippet] Error: Execution timed out."
        except Exception as e:
            return f"[test_snippet] Exception: {traceback.format_exc()}"

    # -------------------- CODE INSPECT --------------------
    def explain_error(self, error_log: str) -> str:
        """Try to interpret an error log and suggest a fix."""
        if "IndentationError" in error_log:
            return "Your indentation is off — make sure your code is consistently spaced."
        if "NameError" in error_log:
            return "A variable or function was used before it was defined."
        if "ImportError" in error_log:
            return "A required module isn't installed or imported correctly."
        if "TypeError" in error_log:
            return "Type mismatch — check variable assignments and function arguments."
        return f"Error analysis:\n{error_log}"

    # -------------------- AUTO FIX --------------------
    def attempt_autofix(self, code: str) -> str:
        """Try to detect simple syntax issues and fix automatically."""
        fixed = code.replace("===", "==").replace("print ", "print(").replace("\n\n\n", "\n\n")
        if not fixed.strip().endswith(")"):
            fixed += ")"
        return self.format_code(fixed)

    # -------------------- PROJECT SCAN --------------------
    def scan_project(self) -> list:
        """List all Python files in the workspace."""
        found = []
        for root, _, files in os.walk(self.workspace):
            for f in files:
                if f.endswith(".py"):
                    found.append(os.path.join(root, f))
        return found
