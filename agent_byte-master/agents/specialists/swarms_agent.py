"""
iSwarmsAI Agent — Distributed Parallel Executor
Skills: fan-out parallel execution, emergent consensus,
        load balancing across worker swarms, aggregation.
"""
from __future__ import annotations
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from core.controllers.memory_controller import memory
from core.controllers.llm_controller import llm
from core.bus.agent_bus import bus
from core.init_dual_brain import initialize_dual_brain

# At startup
dual_brain = initialize_dual_brain(orchestrator=your_orchestrator)

logger = logging.getLogger(__name__)
_POOL = ThreadPoolExecutor(thread_name_prefix="swarms")


class SwarmsSpecialist(BaseAgent):
    """
    Distributed parallel executor. Specialises in:
    - Fan-out: split one task into N parallel sub-tasks
    - Emergent consensus: aggregate N results into one answer
    - Load balancing across worker perspectives
    - High-volume, repetitive task processing
    - Diversity sampling (multiple angles on same problem)
    """

    SKILLS = [
        "parallel task fan-out",
        "emergent consensus aggregation",
        "multi-perspective sampling",
        "high-volume task processing",
        "diversity-based exploration",
    ]

    N_WORKERS = 3   # default parallel workers

    @property
    def name(self) -> str:
        return "iswarmsai"

    @property
    def description(self) -> str:
        return "Distributed swarm executor — parallel workers with consensus aggregation"

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.update_state(status="executing", current_task=task)
        ctx = context or {}
        bus.publish_sync("agent.thinking", {"agent": self.name, "task": task[:80]}, source=self.name)

        # Try native Swarms
        result = self._try_swarms_native(task)
        if result:
            self._store(task, result)
            return result

        # Fallback: simulated swarm (sync-safe parallel workers)
        result = self._simulated_swarm_sync(task, ctx)
        self._store(task, result)
        return result

    def _try_swarms_native(self, task: str) -> Optional[str]:
        try:
            from frameworks.agents.registry import get_framework
            from frameworks.agents.base import AgentSpec, TaskSpec
            fw = get_framework("swarms")
            fw.add_agent(AgentSpec(name="swarm_main", role="executor", goal=task))
            result = fw.run([TaskSpec(description=task, expected_output="output",
                                      agent_name="swarm_main")])
            return str(result.output)
        except Exception as e:
            logger.warning("[Swarms] native framework unavailable (%s), using simulated swarm", e)
            return None

    def _simulated_swarm_sync(self, task: str, ctx: Dict) -> str:
        """Spawn N parallel workers via ThreadPoolExecutor, then aggregate."""
        perspectives = [
            f"Answer this from a {angle} perspective: {task}"
            for angle in ["technical", "practical", "creative"]
        ]
        futures = [_POOL.submit(llm.call, p) for p in perspectives]
        results = []
        for f in futures:
            try:
                results.append(f.result(timeout=60))
            except Exception as e:
                logger.warning("[Swarms] worker failed: %s", e)
                results.append("")
        return self._consensus(task, results)

    def _consensus(self, task: str, results: List[str]) -> str:
        combined = "\n\n".join(f"[Worker {i+1}]: {r[:400]}" for i, r in enumerate(results))
        prompt = (
            f"You are aggregating results from a swarm of parallel workers.\n\n"
            f"Task: {task}\n\n"
            f"Worker outputs:\n{combined}\n\n"
            "Identify the consensus, resolve contradictions, and produce one unified best answer."
        )
        return llm.call(prompt)

    def _store(self, task: str, result: str):
        memory.remember(result, agent_id=self.name, metadata={"task": task, "type": "swarm_output"})
        bus.publish_sync("agent.result", {"agent": self.name, "task": task[:60]}, source=self.name)
