
import logging
from typing import Dict, Any, List
# init_dual_brain removed — wire orchestrator at startup

# At startup
# dual_brain wired at startup

logger = logging.getLogger(__name__)

try:
    from core.diagnostics.agent_byte_monitor import AgentByteMonitor
    _HAS_BYTE_MONITOR = True
except Exception:
    _HAS_BYTE_MONITOR = False
    AgentByteMonitor = None

try:
    from core.brain.agents.tool_agent import tool_agent as skill_library as _skill_library
    _HAS_SKILLS = True
except Exception:
    _HAS_SKILLS = False


class SelfAwareExtensions:
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self._byte_monitor = None
        self._last_checks = {}

    def check_agent_byte(self) -> Dict[str, Any]:
        if not _HAS_BYTE_MONITOR:
            return {"component": "agent_byte", "status": "not_installed"}
        if self.orchestrator and hasattr(self.orchestrator, "agent_byte"):
            agent = self.orchestrator.agent_byte
            if agent is None:
                return {"component": "agent_byte", "status": "not_loaded"}
            if self._byte_monitor is None:
                self._byte_monitor = AgentByteMonitor(agent)
            return self._byte_monitor.check()
        return {"component": "agent_byte", "status": "no_orchestrator"}

    def check_skill_library(self) -> Dict[str, Any]:
        if not _HAS_SKILLS:
            return {"component": "skill_library", "status": "not_installed"}
        try:
            stats = _skill_library.get_stats() if hasattr(_skill_library, "get_stats") else {}
            return {
                "component": "skill_library",
                "status": "healthy",
                "cached_skills": stats.get("count", 0) if isinstance(stats, dict) else 0,
            }
        except Exception as exc:
            return {"component": "skill_library", "status": "error", "error": str(exc)}

    def check_adap_bridge(self) -> Dict[str, Any]:
        try:
            from core.bridges.adap_pipeline_bridge import adap_bridge
            modules = adap_bridge.get_module_list()
            return {
                "component": "adap_bridge",
                "status": "healthy",
                "modules_discovered": len(modules),
                "modules": modules[:10],
            }
        except Exception as exc:
            return {"component": "adap_bridge", "status": "error", "error": str(exc)}

    def run_all(self) -> List[Dict[str, Any]]:
        checks = [
            self.check_agent_byte(),
            self.check_skill_library(),
            self.check_adap_bridge(),
        ]
        for c in checks:
            self._last_checks[c["component"]] = c
        return checks


aware_extensions = SelfAwareExtensions()
