"""CodeExecutor — sandboxed execution of Python/MATLAB code from workflows."""
from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile, time
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_TIMEOUT = 30
DEFAULT_CACHE = Path.home() / ".ghostgoat" / "execution_cache"


class ExecutionResult:
    def __init__(self, code, success, stdout, stderr, returncode, elapsed, cached=False):
        self.code = code
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.elapsed = elapsed
        self.cached = cached

    def to_dict(self):
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "elapsed": self.elapsed,
            "cached": self.cached,
        }


class CodeExecutor:
    def __init__(self, timeout=DEFAULT_TIMEOUT, cache_dir=None, python_bin=sys.executable):
        self.timeout = timeout
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.python_bin = python_bin
        self._cache = {}

    def run_python(self, code, use_cache=True):
        key = self._cache_key(code)
        if use_cache and key in self._cache:
            return self._cache[key]
        if use_cache:
            disk = self.cache_dir / f"{key}.json"
            if disk.exists():
                d = json.loads(disk.read_text(encoding="utf-8"))
                r = ExecutionResult(code, **d)
                self._cache[key] = r
                return r
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp = f.name
        t0 = time.time()
        try:
            proc = subprocess.run(
                [self.python_bin, tmp],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            result = ExecutionResult(
                code=code,
                success=proc.returncode == 0,
                stdout=proc.stdout[:5000],
                stderr=proc.stderr[:5000],
                returncode=proc.returncode,
                elapsed=time.time() - t0,
            )
        except subprocess.TimeoutExpired:
            result = ExecutionResult(
                code=code,
                success=False,
                stdout="",
                stderr=f"Timeout ({self.timeout}s)",
                returncode=-1,
                elapsed=self.timeout,
            )
        except Exception as e:
            result = ExecutionResult(
                code=code,
                success=False,
                stdout="",
                stderr=str(e),
                returncode=-1,
                elapsed=0.0,
            )
        finally:
            Path(tmp).unlink(missing_ok=True)
        if use_cache:
            self._cache[key] = result
            (self.cache_dir / f"{key}.json").write_text(
                json.dumps(result.to_dict(), indent=2), encoding="utf-8"
            )
        return result

    def run_cell(self, wf, cell_index=0, use_cache=True):
        cells = self._collect_cells(wf)
        if not cells:
            return ExecutionResult("", False, "", "No code cells found", -1, 0)
        if cell_index >= len(cells):
            return ExecutionResult(
                "",
                False,
                "",
                f"Cell {cell_index} out of range",
                -1,
                0,
            )
        return self.run_python(cells[cell_index]["code"], use_cache=use_cache)

    def run_all_cells(self, wf, stop_on_error=True):
        cells = self._collect_cells(wf)
        results = []
        for cell in cells:
            r = self.run_python(cell["code"])
            results.append(r)
            if stop_on_error and not r.success:
                break
        return results

    def validate_workflow(self, wf):
        results = self.run_all_cells(wf, stop_on_error=False)
        return {
            "workflow_id": wf.get("workflow_id"),
            "project_name": wf.get("project_name"),
            "cells_total": len(results),
            "cells_passed": sum(1 for r in results if r.success),
            "cells_failed": sum(1 for r in results if not r.success),
            "total_time": sum(r.elapsed for r in results),
            "results": [r.to_dict() for r in results],
        }

    def benchmark(self, workflow_ids, projects_dir):
        reports = []
        for wid in workflow_ids:
            f = projects_dir / f"{wid}.workflow.json"
            if not f.exists():
                continue
            wf = json.loads(f.read_text(encoding="utf-8"))
            reports.append(self.validate_workflow(wf))
        reports.sort(
            key=lambda r: r["cells_passed"] / max(r["cells_total"], 1), reverse=True
        )
        return reports

    def _cache_key(self, code):
        return hashlib.sha256(code.encode()).hexdigest()[:16]

    @staticmethod
    def _collect_cells(wf):
        cells = []
        for node in wf.get("nodes", []):
            ext = node["metadata"].get("extension", "")
            content = node.get("content", {})
            if content.get("type") != "text":
                continue
            raw = content.get("content", "")
            if ext == ".ipynb":
                try:
                    nb = json.loads(raw)
                    for i, cell in enumerate(nb.get("cells", [])):
                        if cell.get("cell_type") == "code":
                            cells.append(
                                {
                                    "file": node["label"],
                                    "cell": i,
                                    "code": "".join(cell.get("source", [])),
                                }
                            )
                except Exception:
                    pass
            elif ext == ".py":
                cells.append({"file": node["label"], "cell": 0, "code": raw})
        return cells
