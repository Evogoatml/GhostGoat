"""
ToolController — unified tool access for all agents.
"""
from __future__ import annotations
import asyncio
import importlib.util
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
_POOL = ThreadPoolExecutor(thread_name_prefix="tool_ctrl")


def _load_tools_via_importlib():
    try:
        path = Path('/home/popic/GhostGoat/agent_byte-master/core/tools.py')
        spec = importlib.util.spec_from_file_location('_gg_tools', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.tools
    except Exception as e:
        logger.debug("[Tools] Direct load failed: %s", e)
        return None


class ToolController:
    _instance: Optional["ToolController"] = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance
    def __init__(self):
        if self._ready:
            return
        self._registry = None
        self._new_registry = None
        self._selector = None
        self._executor = None
        self._adaptive = None
        self._tool_memory = None
        self._ready = True

    def _get_registry(self):
        if self._registry is not None:
            return self._registry
        tools_mod = _load_tools_via_importlib()
        if tools_mod is not None:
            self._registry = tools_mod
            logger.info("GhostGoat tools loaded: %d", len(tools_mod.list_tools()))
            return self._registry
        try:
            from tools.registry import registry
            self._registry = registry
            return registry
        except Exception:
            class Stub:
                def execute_tool(self, name, **kw):
                    class R:
                        success = False
                        output = None
                        error = f"Tool '{name}' missing"
                    return R()
                def list_tools(self):
                    return []
            self._registry = Stub()
            return self._registry

    def run(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        reg = self._get_registry()
        try:
            r = reg.execute_tool(tool_name, **kwargs)
            return {"success": r.success, "output": r.output, "error": r.error}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_tools(self) -> List[str]:
        reg = self._get_registry()
        return reg.list_tools() if reg else []

    def workflow_search(self, query: str, project_type=None, limit=20):
        return self.run("workflow_search", query=query, project_type=project_type, limit=limit)

    def workflow_summary(self, name_or_id: str):
        return self.run("workflow_summary", name_or_id=name_or_id)

    def workflow_run(self, name_or_id: str, cell_index=0):
        return self.run("workflow_run", name_or_id=name_or_id, cell_index=cell_index)

    def workflow_list(self, project_type=None, min_nodes=0):
        return self.run("workflow_list", project_type=project_type, min_nodes=min_nodes)

    async def run_async(self, tool_name: str, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_POOL, lambda: self.run(tool_name, **kwargs))

    def select_tools(self, task: str, fast_mode=False):
        return []
    def run_tools(self, selections, context=None):
        return [{"error": "not available", "success": False}]
    def run_adaptive(self, goal: str):
        return {"error": "not available"}
    def get_insights(self):
        return []


tools = ToolController()