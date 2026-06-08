"""
WorkflowTools
=============

GhostGoat-native integration for the workflow registry.

Provides tools callable from ToolController and agents:
  - workflow_search(query)     → full-text search across all workflows
  - workflow_summary(name)     → inspect a project
  - workflow_run(name, cell)   → execute a code cell safely
  - workflow_ingest()          → index all workflows into CentralNeuralBackend

Usage from an agent:
    from core.controllers.tool_controller import ToolController
    tc = ToolController()
    hits = tc.run("workflow_search", query="sklearn kmeans")
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── paths to the standalone orchestrator (zero core.* deps) ─────────────────

WORKFLOW_ROOT = Path("/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows")
PROJECTS_DIR = WORKFLOW_ROOT / "projects"
MASTER = WORKFLOW_ROOT / "master_workflow_registry.json"
ORCHESTRATOR = WORKFLOW_ROOT / "workflow_orchestrator.py"


def _load_master() -> Dict[str, Any]:
    with open(MASTER, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_workflow(name_or_id: str) -> Optional[Dict[str, Any]]:
    direct = PROJECTS_DIR / f"{name_or_id}.workflow.json"
    if direct.exists():
        with open(direct, "r", encoding="utf-8") as f:
            return json.load(f)
    master = _load_master()
    for p in master["projects"]:
        if p["workflow_id"] == name_or_id or p["project_name"] == name_or_id:
            with open(PROJECTS_DIR / Path(p["workflow_file"]).name, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


# ═════════════════════════════════════════════════════════════════════════════
#  Tool functions → these are what ToolController registers
# ═════════════════════════════════════════════════════════════════════════════

def search(query: str, project_type: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """Full-text search across all workflow file contents."""
    q = query.lower()
    results: List[Dict[str, Any]] = []
    master = _load_master()

    for project in master["projects"]:
        if project_type and project["project_type"] != project_type:
            continue
        wf = _load_workflow(project["workflow_id"])
        if not wf:
            continue
        for node in wf.get("nodes", []):
            content = node.get("content", {})
            text = ""
            if content.get("type") == "text":
                text = content.get("content", "")
            label = node.get("label", "")
            score = text.lower().count(q) + label.lower().count(q)
            if score > 0:
                results.append({
                    "project": wf["project_name"],
                    "workflow_id": wf["workflow_id"],
                    "file": label,
                    "file_path": node.get("file_path"),
                    "score": score,
                })

    results.sort(key=lambda x: -x["score"])
    return {
        "query": query,
        "total": len(results),
        "results": results[:limit],
    }


def summary(name_or_id: str) -> Dict[str, Any]:
    """Return project summary: nodes, roles, imports, code snippets."""
    wf = _load_workflow(name_or_id)
    if not wf:
        return {"error": f"Project '{name_or_id}' not found", "success": False}

    nodes = wf.get("nodes", [])
    roles: Dict[str, int] = {}
    exts: Dict[str, int] = {}
    imports = set()
    code_snippets = 0

    for node in nodes:
        md = node["metadata"]
        roles[md["role"]] = roles.get(md["role"], 0) + 1
        exts[md["extension"]] = exts.get(md["extension"], 0) + 1

        content = node.get("content", {})
        if content.get("type") != "text":
            continue

        raw = content.get("content", "")
        ext = md["extension"]
        # count python code cells / imports
        if ext in (".py", ".ipynb"):
            if ext == ".ipynb":
                try:
                    nb = json.loads(raw)
                    for cell in nb.get("cells", []):
                        if cell.get("cell_type") == "code":
                            code_snippets += 1
                            src = "".join(cell.get("source", []))
                            for line in src.splitlines():
                                line = line.strip()
                                if line.startswith("import ") or line.startswith("from "):
                                    imports.add(line)
                except Exception:
                    pass
            else:
                for line in raw.splitlines():
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        imports.add(line)

    return {
        "success": True,
        "project_name": wf["project_name"],
        "workflow_id": wf["workflow_id"],
        "project_type": wf["project_type"],
        "agent_id": wf.get("agent", {}).get("agent_id"),
        "nodes": len(nodes),
        "roles": roles,
        "extensions": exts,
        "code_snippets": code_snippets,
        "imports": sorted(imports)[:50],
        "source_path": wf["source_path"],
    }


def run_cell(name_or_id: str, cell_index: int = 0) -> Dict[str, Any]:
    """Extract and execute a specific code cell from a workflow project."""
    wf = _load_workflow(name_or_id)
    if not wf:
        return {"error": f"Project '{name_or_id}' not found", "success": False}

    # Collect all code snippets in order
    snippets: List[Dict[str, Any]] = []
    for node in wf.get("nodes", []):
        md = node["metadata"]
        content = node.get("content", {})
        if content.get("type") != "text":
            continue
        raw = content.get("content", "")

        if md["extension"] == ".ipynb":
            try:
                nb = json.loads(raw)
                for i, cell in enumerate(nb.get("cells", [])):
                    if cell.get("cell_type") == "code":
                        snippets.append({
                            "file": node["label"],
                            "cell": i,
                            "code": "".join(cell.get("source", [])),
                        })
            except Exception:
                pass
        elif md["extension"] == ".py":
            snippets.append({
                "file": node["label"],
                "cell": 0,
                "code": raw,
            })

    if cell_index >= len(snippets):
        return {
            "error": f"Cell {cell_index} out of range (max {len(snippets)})",
            "success": False,
        }

    snippet = snippets[cell_index]
    code = snippet["code"]

    # Execute safely in subprocess
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True, timeout=30,
        )
        return {
            "success": result.returncode == 0,
            "file": snippet["file"],
            "cell": snippet["cell"],
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
            "rc": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout (30s)", "file": snippet["file"], "cell": snippet["cell"]}
    except Exception as e:
        return {"success": False, "error": str(e), "file": snippet["file"], "cell": snippet["cell"]}
    finally:
        Path(tmp).unlink(missing_ok=True)


def list_projects(project_type: Optional[str] = None, min_nodes: int = 0) -> Dict[str, Any]:
    """List workflow projects matching criteria."""
    master = _load_master()
    projects = []
    for p in master["projects"]:
        if project_type and p["project_type"] != project_type:
            continue
        if p["node_count"] < min_nodes:
            continue
        projects.append({
            "name": p["project_name"],
            "workflow_id": p["workflow_id"],
            "type": p["project_type"],
            "nodes": p["node_count"],
            "agent_id": p.get("agent_id"),
        })
    return {"total": len(projects), "projects": projects}


def ingest_backend() -> Dict[str, Any]:
    """Index all workflow files into CentralNeuralBackend."""
    from core.ordinance.central_backend import CentralNeuralBackend

    backend = CentralNeuralBackend()
    indexed = 0
    for wf_file in PROJECTS_DIR.glob("*.workflow.json"):
        path = str(wf_file.resolve())
        result = backend.index_file(path)
        if result is not None:
            indexed += 1

    # Register workflows as a virtual agent
    backend.register_agent(
        str(WORKFLOW_ROOT),
        str(MASTER),
    )

    return {
        "success": True,
        "indexed": indexed,
        "backend_dir": backend.backend_dir,
    }


# ═════════════════════════════════════════════════════════════════════════════
#  ToolRegistry-compatible wrapper (for ToolController._get_registry)
# ═════════════════════════════════════════════════════════════════════════════

class WorkflowToolRegistry:
    """
    Minimal tool-registry interface that ToolController can consume.
    Wraps the standalone functions above.
    """

    TOOLS = {
        "workflow_search":  search,
        "workflow_summary": summary,
        "workflow_run":     run_cell,
        "workflow_list":    list_projects,
        "workflow_ingest":  ingest_backend,
    }

    @property
    def tools(self) -> Dict[str, Any]:
        return self.TOOLS

    def execute_tool(self, name: str, **kwargs) -> Any:
        if name not in self.TOOLS:
            class Result:
                success = False
                output = None
                error = f"Tool '{name}' not in WorkflowToolRegistry"
            return Result()
        try:
            out = self.TOOLS[name](**kwargs)
            class Result:
                pass
            r = Result()
            r.success = out.get("success", True) if isinstance(out, dict) else True
            r.output = out
            r.error = None
            return r
        except Exception as e:
            import traceback
            class Result:
                success = False
                output = None
                error = f"{e}\n{traceback.format_exc()}"
            return Result()

    def list_tools(self) -> List[str]:
        return list(self.TOOLS.keys())


# Singleton
registry = WorkflowToolRegistry()
