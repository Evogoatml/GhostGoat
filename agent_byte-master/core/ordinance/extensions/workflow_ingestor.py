"""
WorkflowIngestor
================

Ingests the 421 workflow JSON files into the CentralNeuralBackend so they become
first-class citizens in the GhostGoat knowledge graph.

Usage:
    from core.ordinance.extensions.workflow_ingestor import WorkflowIngestor
    ingestor = WorkflowIngestor()
    ingestor.ingest_all()
    
    # Now query via OrdinanceClient:
    # client.search("k-nearest neighbour sklearn")
    # client.get_folder_context("brain/knowledge/processed/workflows/projects")
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.ordinance.central_backend import CentralNeuralBackend


WORKFLOW_ROOT = Path("/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows")
PROJECTS_DIR = WORKFLOW_ROOT / "projects"
MASTER = WORKFLOW_ROOT / "master_workflow_registry.json"


class WorkflowIngestor:
    """Loads workflow JSONs into the CentralNeuralBackend knowledge graph."""

    def __init__(self, backend: Optional[CentralNeuralBackend] = None):
        self.backend = backend or CentralNeuralBackend(str(Path(__file__).resolve().parents[5]))
        self._loaded: Set[str] = set()

    # ── public API ───────────────────────────────────────────────────────────

    def ingest_all(self) -> Dict[str, int]:
        """Ingest every workflow in projects/ and the master registry."""
        stats = {"workflows": 0, "nodes": 0, "agents": 0}

        if not MASTER.exists():
            raise FileNotFoundError(f"Master registry missing: {MASTER}")

        master = json.loads(MASTER.read_text(encoding="utf-8"))

        for project in master.get("projects", []):
            wf_path = WORKFLOW_ROOT / Path(project["workflow_file"]).name
            if not wf_path.exists():
                continue

            wf = json.loads(wf_path.read_text(encoding="utf-8"))
            self._ingest_workflow(wf, project)
            stats["workflows"] += 1
            stats["nodes"] += len(wf.get("nodes", []))
            if project.get("agent_id"):
                stats["agents"] += 1

        # Index the master registry itself as a top-level context
        self.backend.index_file(
            str(MASTER),
            meta={"type": "workflow_registry", "projects": stats["workflows"]}
        )

        return stats

    def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """Load a single workflow by ID."""
        for wf_file in PROJECTS_DIR.glob("*.workflow.json"):
            wf = json.loads(wf_file.read_text(encoding="utf-8"))
            if wf.get("workflow_id") == workflow_id:
                return wf
        return None

    def search_workflows(self, query: str, project_type: Optional[str] = None) -> List[Dict]:
        """Full-text search across all workflow nodes."""
        results = []
        query_lower = query.lower()

        for wf_file in PROJECTS_DIR.glob("*.workflow.json"):
            wf = json.loads(wf_file.read_text(encoding="utf-8"))
            if project_type and wf.get("project_type") != project_type:
                continue

            for node in wf.get("nodes", []):
                content = node.get("content", {})
                text = ""
                if content.get("type") == "text":
                    text = content.get("content", "")
                label = node.get("label", "")
                file_path = node.get("file_path", "")

                if query_lower in text.lower() or query_lower in label.lower():
                    results.append({
                        "workflow_id": wf["workflow_id"],
                        "project_name": wf["project_name"],
                        "node_id": node["node_id"],
                        "label": label,
                        "file_path": file_path,
                        "score": text.lower().count(query_lower),
                    })

        # Sort by score desc
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:50]

    def get_project_by_name(self, name: str) -> Optional[Dict]:
        """Find workflow by project name (exact or partial)."""
        name_lower = name.lower()
        for wf_file in PROJECTS_DIR.glob("*.workflow.json"):
            wf = json.loads(wf_file.read_text(encoding="utf-8"))
            if name_lower in wf.get("project_name", "").lower():
                return wf
        return None

    def list_by_type(self, project_type: str) -> List[Dict]:
        """List all workflows of a given type."""
        out = []
        for wf_file in PROJECTS_DIR.glob("*.workflow.json"):
            wf = json.loads(wf_file.read_text(encoding="utf-8"))
            if wf.get("project_type") == project_type:
                out.append({
                    "workflow_id": wf["workflow_id"],
                    "project_name": wf["project_name"],
                    "node_count": len(wf.get("nodes", [])),
                })
        return out

    # ── private ───────────────────────────────────────────────────────────────

    def _ingest_workflow(self, wf: Dict, project_meta: Dict):
        """Add workflow nodes into the backend index."""
        wf_id = wf["workflow_id"]
        if wf_id in self._loaded:
            return
        self._loaded.add(wf_id)

        # Index each node as a virtual "file"
        for node in wf.get("nodes", []):
            virtual_path = f"workflow://{wf_id}/{node['node_id']}"
            content = node.get("content", {})
            text_preview = ""
            if content.get("type") == "text":
                text_preview = content.get("content", "")[:500]

            self.backend.index_file(
                virtual_path,
                meta={
                    "project": wf["project_name"],
                    "workflow_id": wf_id,
                    "node_id": node["node_id"],
                    "label": node["label"],
                    "extension": node["metadata"]["extension"],
                    "role": node["metadata"]["role"],
                    "text_preview": text_preview,
                    "agent": wf.get("agent"),
                }
            )

        # Register agent if present
        agent = wf.get("agent")
        if agent and agent.get("agent_id"):
            self.backend.agent_registry[agent["agent_id"]] = {
                "folder": wf.get("source_path", ""),
                "last_updated": wf.get("generated_at", ""),
                "workflow_id": wf_id,
                "node_count": len(wf.get("nodes", [])),
            }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest workflows into GhostGoat")
    parser.add_argument("--ingest", action="store_true", help="Run full ingestion")
    parser.add_argument("--search", type=str, help="Search workflows")
    parser.add_argument("--type", type=str, help="Filter by project type")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    args = parser.parse_args()

    ingestor = WorkflowIngestor()

    if args.ingest:
        stats = ingestor.ingest_all()
        print(f"Ingested {stats['workflows']} workflows, {stats['nodes']} nodes, {stats['agents']} agents")

    if args.search:
        results = ingestor.search_workflows(args.search, args.type)
        for r in results[:10]:
            print(f"  [{r['project_name']}] {r['label']} (score:{r['score']})")

    if args.stats:
        for wf_file in PROJECTS_DIR.glob("*.workflow.json"):
            wf = json.loads(wf_file.read_text(encoding="utf-8"))
            print(f"{wf['project_name']:40} | {wf['project_type']:15} | {len(wf['nodes']):4} nodes")
