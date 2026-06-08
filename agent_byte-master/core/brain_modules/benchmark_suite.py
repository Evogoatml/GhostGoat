"""BenchmarkSuite — continuous integration for workflow code."""
from __future__ import annotations
import hashlib, json, subprocess, sys, tempfile, time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path(
    "/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows/projects"
)
HISTORY_DIR = Path.home() / ".ghostgoat" / "benchmark_history"


class BenchmarkSuite:
    def __init__(self, projects_dir=None, history_dir=None, timeout=30):
        self.projects_dir = projects_dir or PROJECTS_DIR
        self.history_dir = Path(history_dir) if history_dir else HISTORY_DIR
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def test_workflow(self, workflow_id):
        f = self.projects_dir / f"{workflow_id}.workflow.json"
        if not f.exists():
            return {"error": f"Workflow {workflow_id} not found", "success": False}
        wf = json.loads(f.read_text(encoding="utf-8"))
        cells = self._collect_cells(wf)
        results = []
        for idx, cell in enumerate(cells):
            t0 = time.time()
            r = self._run_python(cell["code"])
            results.append(
                {
                    "cell_index": idx,
                    "file": cell["file"],
                    "success": r["success"],
                    "stdout": r["stdout"][:500],
                    "stderr": r["stderr"][:500],
                    "elapsed": round(time.time() - t0, 3),
                }
            )
        passed = sum(1 for r in results if r["success"])
        report = {
            "workflow_id": workflow_id,
            "project_name": wf.get("project_name"),
            "project_type": wf.get("project_type"),
            "cells_total": len(results),
            "cells_passed": passed,
            "cells_failed": len(results) - passed,
            "pass_rate": passed / max(len(results), 1),
            "total_time": sum(r["elapsed"] for r in results),
            "timestamp": time.time(),
            "results": results,
            "workflow_hash": self._hash_workflow(wf),
        }
        self._save_history(workflow_id, report)
        return report

    def test_domain(self, domain):
        reports = []
        for f in self.projects_dir.glob("*.workflow.json"):
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if wf.get("project_type") == domain:
                reports.append(self.test_workflow(wf.get("workflow_id", f.stem)))
        reports.sort(key=lambda r: r.get("pass_rate", 0), reverse=True)
        return reports

    def test_all(self, limit=None):
        reports = []
        files = sorted(self.projects_dir.glob("*.workflow.json"))
        if limit:
            files = files[:limit]
        for f in files:
            reports.append(self.test_workflow(f.stem))
        reports.sort(key=lambda r: r.get("pass_rate", 0), reverse=True)
        return reports

    def detect_regression(self, workflow_id):
        history = self._load_history(workflow_id)
        if len(history) < 2:
            return None
        current, baseline = history[-1], history[-2]
        regressions = []
        for cur, base in zip(current["results"], baseline["results"]):
            if not cur["success"] and base["success"]:
                regressions.append(
                    {
                        "cell_index": cur["cell_index"],
                        "file": cur["file"],
                        "previous": "PASS",
                        "current": "FAIL",
                        "stderr": cur["stderr"],
                    }
                )
        return {
            "workflow_id": workflow_id,
            "baseline_hash": baseline.get("workflow_hash"),
            "current_hash": current.get("workflow_hash"),
            "pass_rate_delta": current["pass_rate"] - baseline["pass_rate"],
            "regressions": regressions,
            "regression_count": len(regressions),
        }

    def leaderboard(self, domain=None):
        reports = []
        for f in self.projects_dir.glob("*.workflow.json"):
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if domain and wf.get("project_type") != domain:
                continue
            wid = wf.get("workflow_id", f.stem)
            history = self._load_history(wid)
            if not history:
                continue
            latest = history[-1]
            reports.append(
                {
                    "workflow_id": wid,
                    "project_name": latest["project_name"],
                    "pass_rate": latest["pass_rate"],
                    "cells_total": latest["cells_total"],
                    "total_time": latest["total_time"],
                    "last_tested": latest["timestamp"],
                }
            )
        reports.sort(key=lambda r: r["pass_rate"], reverse=True)
        return reports

    def _run_python(self, code):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp = f.name
        try:
            proc = subprocess.run(
                [sys.executable, tmp],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Timeout", "returncode": -1}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}
        finally:
            Path(tmp).unlink(missing_ok=True)

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

    @staticmethod
    def _hash_workflow(wf):
        return hashlib.sha256(json.dumps(wf, sort_keys=True).encode()).hexdigest()[:16]

    def _save_history(self, wid, report):
        with open(self.history_dir / f"{wid}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(report) + "\n")

    def _load_history(self, wid):
        p = self.history_dir / f"{wid}.jsonl"
        if not p.exists():
            return []
        with open(p, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
