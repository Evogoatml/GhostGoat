"""
WorkflowTools
=============

Tools that expose the 421 workflow projects through the GhostGoat ToolController.

Usage:
    from core.ordinance.extensions.workflow_tools import WorkflowTools
    wt = WorkflowTools()
    
    # Search all training code
    results = wt.search_training_code("kmeans sklearn")
    
    # Get a project summary
    summary = wt.get_project_summary("trainer")
    
    # Execute a notebook cell
    result = wt.run_training_cell("training_files", cell_index=0)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ordinance.extensions.workflow_ingestor import WorkflowIngestor
from brain.knowledge.processed.workflows.engines.training_engine import TrainingEngine


class WorkflowTools:
    """Tool interface for the GhostGoat workflow registry."""

    def __init__(self):
        self.ingestor = WorkflowIngestor()
        self.engine = TrainingEngine()

    # ── search tools ──────────────────────────────────────────────────────────

    def search_training_code(self, query: str, project_type: Optional[str] = None) -> List[Dict]:
        """Full-text search across all workflow file contents."""
        return self.ingestor.search_workflows(query, project_type)

    def list_projects(self, project_type: Optional[str] = None) -> List[Dict]:
        """List all available training projects."""
        return self.engine.list_projects(project_type)

    def get_project_summary(self, name: str) -> Dict[str, Any]:
        """Get a human-readable summary of a project."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return {"error": f"Project '{name}' not found"}
        return self.engine.get_summary(wf)

    # ── content access ────────────────────────────────────────────────────────

    def get_project_code(self, name: str, language: str = "python") -> List[Dict]:
        """Extract all code from a project."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return []
        return self.engine.extract_code(wf, language)

    def get_imports(self, name: str) -> List[str]:
        """List all imports a project uses."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return []
        return self.engine.extract_imports(wf)

    def get_dependencies(self, name: str) -> Dict[str, List[str]]:
        """Map standard vs third-party dependencies."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return {"standard": [], "third_party": []}
        return self.engine.analyze_dependencies(wf)

    # ── execution ───────────────────────────────────────────────────────────────

    def run_training_cell(self, name: str, cell_index: int = 0, timeout: int = 30) -> Dict[str, Any]:
        """Execute a specific code cell from a project."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return {"success": False, "error": f"Project '{name}' not found"}
        
        snippets = self.engine.extract_code(wf, language="python")
        if cell_index >= len(snippets):
            return {"success": False, "error": f"Cell {cell_index} out of range (max {len(snippets)})")
        
        return self.engine.run_cell(snippets[cell_index], timeout)

    def run_project(self, name: str, max_cells: int = 5) -> List[Dict]:
        """Execute up to N cells from a project."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return [{"success": False, "error": f"Project '{name}' not found"}]
        return self.engine.run_workflow(wf, max_cells)

    # ── notebook-specific ─────────────────────────────────────────────────────

    def get_notebook_cells(self, name: str) -> List[Dict]:
        """Extract all cells from notebook projects."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return []
        
        cells = []
        for node in wf.get("nodes", []):
            if node["metadata"]["extension"] != ".ipynb":
                continue
            content = node.get("content", {})
            if content.get("type") != "text":
                continue
            try:
                nb = json.loads(content["content"])
                for i, cell in enumerate(nb.get("cells", [])):
                    cells.append({
                        "file": node["label"],
                        "index": i,
                        "type": cell.get("cell_type"),
                        "source": "".join(cell.get("source", [])),
                    })
            except Exception:
                pass
        return cells

    def get_markdown_docs(self, name: str) -> List[Dict]:
        """Extract markdown cells (documentation) from notebooks."""
        wf = self.engine.load_workflow(name)
        if not wf:
            return []
        return self.engine.extract_markdown(wf)

    # ── registry stats ────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Overall workflow registry statistics."""
        projects = self.engine.list_projects()
        types = {}
        total_nodes = 0
        for p in projects:
            types[p["project_type"]] = types.get(p["project_type"], 0) + 1
            total_nodes += p["node_count"]
        return {
            "projects": len(projects),
            "total_nodes": total_nodes,
            "by_type": types,
            "top_projects": sorted(projects, key=lambda x: -x["node_count"])[:10],
        }


if __name__ == "__main__":
    wt = WorkflowTools()
    print(wt.stats())
