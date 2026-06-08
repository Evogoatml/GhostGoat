"""
Agent K — Skill Specialist
Skills: pattern matching, instant recall, code execution, crypto, system ops.
Looks up stored solutions before calling the LLM. Records new successes.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from agents.base import BaseAgent
from core.controllers.memory_controller import memory
from core.controllers.tool_controller import tools
from core.controllers.llm_controller import llm
from core.bus.agent_bus import bus
from core.init_dual_brain import initialize_dual_brain

# At startup
dual_brain = initialize_dual_brain(orchestrator=your_orchestrator)

logger = logging.getLogger(__name__)


class AgentK(BaseAgent):
    """
    Fast, skill-first agent. Specialises in:
    - Known solution recall (skill library)
    - Code execution and debugging
    - Cryptography and hashing
    - File system and system info ops
    - Port / network scanning
    """

    SKILLS = [
        "recall stored solutions",
        "execute python code",
        "compute hashes",
        "encrypt / decrypt data",
        "scan files and directories",
        "system information",
        "port scanning",
        "quick HTTP checks",
    ]

    @property
    def name(self) -> str:
        return "agent_k"

    @property
    def description(self) -> str:
        return "Skill specialist — fast recall and code/crypto/system execution"

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.update_state(status="executing", current_task=task)
        ctx = context or {}
        bus.publish_sync("agent.thinking", {"agent": self.name, "task": task[:80]}, source=self.name)

        # 1. Check skill library first
        result = self._try_skill_library(task)
        if result:
            self._record_success(task, result)
            return result

        # 2. Route to specialised tool handlers
        result = self._route_to_tool(task, ctx)
        if result:
            self._record_success(task, result)
            return result

        # 3. Fall back to LLM with skill context
        recalled = memory.recall(task, agent_id=self.name, k=3)
        context_str = "\n".join(r["content"][:200] for r in recalled)
        prompt = (
            f"You are Agent K, a skill specialist.\n"
            f"Task: {task}\n"
            f"Relevant past knowledge:\n{context_str}\n\n"
            "Solve this efficiently using your skills."
        )
        result = llm.call(prompt)
        self._record_success(task, result)
        return result

    def _try_skill_library(self, task: str) -> Optional[str]:
        try:
            from core.brain.agents import tool_agent as skill_library
            skill = skill_library.lookup(task)
            if skill:
                logger.info("[AgentK] skill cache hit for: %s", task[:40])
                return skill.solution
        except Exception as e:
            logger.debug("[AgentK] skill library error: %s", e)
        return None

    def _route_to_tool(self, task: str, ctx: Dict) -> Optional[str]:
        tl = task.lower()
        if any(w in tl for w in ["hash", "sha", "md5", "checksum"]):
            text = ctx.get("text", task)
            return tools.run("hash", text=text, algorithm="sha256").get("output", "")
        if any(w in tl for w in ["port scan", "open ports", "scan host"]):
            host = ctx.get("host", "localhost")
            return tools.run("port_scan", host=host, ports=ctx.get("ports", [80, 443, 22])).get("output", "")
        if any(w in tl for w in ["list files", "scan directory", "ls "]):
            path = ctx.get("path", ".")
            return tools.run("list_directory", path=path).get("output", "")
        if any(w in tl for w in ["system info", "cpu", "memory usage", "disk"]):
            return tools.run("system_info").get("output", "")
        return None

    def _record_success(self, task: str, result: str):
        try:
            from core.brain.agents import tool_agent as skill_library
            skill_library.record(task, result, success=True)
        except Exception:
            pass
        memory.remember(f"Task: {task}\nResult: {result}", agent_id=self.name,
                        metadata={"type": "execution_record"})
        bus.publish_sync("agent.result", {"agent": self.name, "task": task[:60],
                                           "result": result[:200]}, source=self.name)
