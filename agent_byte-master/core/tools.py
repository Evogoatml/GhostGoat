import sys

"""
Tools — Unified tool interface for GhostGoat agents.
Workflow registry integration added 2026-05-13.
Gracefully degrades if db/core.rag are unavailable.
"""
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── optional GhostGoat deps ─────────────────────────────────────────────────
try:
    from db.repository import TaskRepository
    from core.rag import RAGManager
    _HAS_DB = True
except Exception:
    _HAS_DB = False
    logger.debug("[Tools] db.repository or core.rag unavailable")

# ── workflow tools (always available) ────────────────────────────────────────
def _load_workflow_tools():
    if not hasattr(_load_workflow_tools, "_mod"):
        path = Path('/home/popic/GhostGoat/agent_byte-master/core/workflow_tools.py')
        spec = importlib.util.spec_from_file_location('_gg_workflows', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _load_workflow_tools._mod = mod
    return _load_workflow_tools._mod


class Tools:
    def __init__(self):
        self.repo = None
        self.rag = None
        if _HAS_DB:
            try:
                self.repo = TaskRepository()
                self.rag = RAGManager()
            except Exception as e:
                logger.debug("[Tools] DB init failed: %s", e)

    # ── Task management (requires db) ───────────────────────────────────────
    def create_task(self, title: str, description="", due_date=None, priority="medium"):
        if not self.repo:
            return {"success": False, "error": "TaskRepository not available"}
        task = self.repo.create_task(title, description, due_date, priority)
        self.rag.add_task(task.id, f"{title}: {description}", {"priority": priority})
        return {"success": True, "task_id": task.id, "message": f"Task created: {title}"}

    def list_tasks(self, status=None, priority=None):
        if not self.repo:
            return {"success": False, "error": "TaskRepository not available"}
        return self.repo.list_tasks(status, priority)

    def update_task(self, task_id, status=None, title=None):
        if not self.repo:
            return {"success": False, "error": "TaskRepository not available"}
        return self.repo.update_task(task_id, status, title)

    # ── Workflow Tools (always available) ───────────────────────────────────
    def workflow_search(self, query: str, project_type=None, limit=20):
        mod = _load_workflow_tools()
        return mod.search(query, project_type, limit)

    def workflow_summary(self, name_or_id: str):
        mod = _load_workflow_tools()
        return mod.summary(name_or_id)

    def workflow_run(self, name_or_id: str, cell_index=0):
        mod = _load_workflow_tools()
        return mod.run_cell(name_or_id, cell_index)

    def workflow_list(self, project_type=None, min_nodes=0):
        mod = _load_workflow_tools()
        return mod.list_projects(project_type, min_nodes)

    def workflow_ingest(self):
        mod = _load_workflow_tools()
        return mod.ingest_backend()

    # ── Brain Module Tools (workflow intelligence layer) ─────────────────────
    def _load_brain(self):
        """Lazy-load workflow brain modules via importlib to avoid circular imports."""
        if not hasattr(self, "_brain_mod"):
            try:
                path = Path('/home/popic/GhostGoat/agent_byte-master/core/brain_modules/workflow_skill_manager.py')
                spec = importlib.util.spec_from_file_location('_gg_brain', path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules['_gg_brain'] = mod
                spec.loader.exec_module(mod)
                self._brain_mod = mod.WorkflowSkillManager()
            except Exception as e:
                logger.debug("[Tools] Brain load failed: %s", e)
                self._brain_mod = None
        return self._brain_mod

    def workflow_cycle(self, query: str, execute_code: bool = False):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        return brain.cycle(query, execute_code=execute_code)

    def workflow_few_shot(self, instruction: str, domain: str = None, shots: int = 3, chain_of_thought: bool = False):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        return {"success": True, "prompt": brain.few_shot(instruction, domain=domain, shots=shots, chain_of_thought=chain_of_thought)}

    def workflow_search_semantic(self, query: str, top_k: int = 5):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        return {"success": True, "results": brain.search(query, top_k=top_k)}

    def workflow_execute(self, workflow_id: str, cell: int = 0):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        return brain.execute(workflow_id, cell=cell)

    def workflow_feedback(self, query: str, workflow_id: str, success: bool):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        brain.feedback(query, workflow_id, success)
        return {"success": True, "message": f"Feedback recorded for {workflow_id}"}

    def workflow_route(self, query: str):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        return {"success": True, "domain": brain.route(query)}

    def workflow_benchmark(self, workflow_id: str = None, domain: str = None):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        return {"success": True, "reports": brain.benchmark(workflow_id=workflow_id, domain=domain)}

    def workflow_manifests(self):
        brain = self._load_brain()
        if brain is None:
            return {"success": False, "error": "Brain modules not available"}
        return {"success": True, "manifests": brain.learn_manifests()}

    # ── ToolRegistry-compatible entry point ─────────────────────────────────
    def execute_tool(self, name, **kwargs):
        method = getattr(self, name, None)
        if method:
            try:
                result = method(**kwargs)
            except Exception as e:
                class R:
                    success = False
                    output = None
                    error = str(e)
                return R()
            class R:
                pass
            r = R()
            if isinstance(result, dict):
                r.success = result.get("success", True)
                r.output = result
                r.error = result.get("error") if not r.success else None
            else:
                r.success = True
                r.output = result
                r.error = None
            return r
        class R:
            success = False
            output = None
            error = f"Tool '{name}' not available"
        return R()

    def list_tools(self):
        base = []
        if _HAS_DB:
            base += ["create_task", "list_tasks", "update_task"]
        base += [
            "workflow_search", "workflow_summary", "workflow_run",
            "workflow_list", "workflow_ingest",
            "workflow_cycle", "workflow_few_shot", "workflow_search_semantic",
            "workflow_execute", "workflow_feedback", "workflow_route",
            "workflow_benchmark", "workflow_manifests",
        ]
        return base


# Singleton
tools = Tools()
