"""
SuperAGI Agent — Autonomous Goal Decomposer & Meta-Reasoner
Skills: break goals into sub-tasks, self-reflection, recursive planning,
        long-horizon reasoning, capability gap analysis.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from core.controllers.memory_controller import memory
from core.controllers.llm_controller import llm
from core.bus.agent_bus import bus
from core.init_dual_brain import initialize_dual_brain

# At startup
dual_brain = initialize_dual_brain(orchestrator=your_orchestrator)

logger = logging.getLogger(__name__)


class SuperAGIAgent(BaseAgent):
    """
    Long-horizon autonomous agent. Specialises in:
    - Recursive goal decomposition
    - Capability gap analysis (what do we NOT know yet?)
    - Self-reflection on reasoning quality
    - Multi-step planning with dependency tracking
    - Proposing new agents/skills the system needs
    """

    SKILLS = [
        "recursive goal decomposition",
        "capability gap analysis",
        "multi-step planning",
        "self-reflection",
        "dependency tracking",
        "propose system improvements",
    ]

    @property
    def name(self) -> str:
        return "superagi"

    @property
    def description(self) -> str:
        return "Autonomous goal decomposer — breaks complex goals into executable sub-tasks"

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.update_state(status="executing", current_task=task)
        ctx = context or {}
        bus.publish_sync("agent.thinking", {"agent": self.name, "task": task[:80]}, source=self.name)

        # Decompose the goal
        sub_tasks = self._decompose(task, ctx)

        # Reflect on gaps
        gaps = self._find_gaps(task, sub_tasks)

        # Build execution plan
        plan = self._build_plan(task, sub_tasks, gaps)

        result = json.dumps(plan, indent=2)
        memory.remember(f"Goal: {task}\nPlan: {result}", agent_id=self.name,
                        metadata={"type": "goal_plan"})
        bus.publish_sync("agent.result", {"agent": self.name, "task": task[:60],
                                           "plan_steps": len(sub_tasks)}, source=self.name)
        return result

    def _decompose(self, goal: str, ctx: Dict) -> List[str]:
        prior = memory.recall(goal, agent_id=self.name, k=3)
        prior_str = "\n".join(r["content"][:150] for r in prior)
        prompt = (
            f"Decompose this goal into 3-7 concrete, executable sub-tasks.\n\n"
            f"Goal: {goal}\n"
            f"Context: {json.dumps(ctx, default=str)[:400]}\n"
            f"Past plans: {prior_str}\n\n"
            'Return ONLY valid JSON: {"sub_tasks": ["task1", "task2", ...]}'
        )
        raw = llm.call(prompt)
        try:
            return json.loads(raw).get("sub_tasks", [goal])
        except Exception:
            return [goal]

    def _find_gaps(self, goal: str, sub_tasks: List[str]) -> List[str]:
        prompt = (
            f"Given this goal and sub-tasks, what capabilities or information are MISSING?\n\n"
            f"Goal: {goal}\nSub-tasks: {sub_tasks}\n\n"
            'Return ONLY valid JSON: {"gaps": ["gap1", "gap2"]}'
        )
        raw = llm.call(prompt)
        try:
            return json.loads(raw).get("gaps", [])
        except Exception:
            return []

    def _build_plan(self, goal: str, sub_tasks: List[str], gaps: List[str]) -> Dict:
        return {
            "goal": goal,
            "sub_tasks": [{"step": i+1, "task": t, "status": "pending"}
                          for i, t in enumerate(sub_tasks)],
            "capability_gaps": gaps,
            "recommended_agents": self._recommend_agents(sub_tasks),
        }

    def _recommend_agents(self, sub_tasks: List[str]) -> Dict[str, List[str]]:
        mapping: Dict[str, List[str]] = {}
        for task in sub_tasks:
            tl = task.lower()
            if any(w in tl for w in ["code", "script", "execute", "hash", "crypto"]):
                mapping[task] = ["agent_k"]
            elif any(w in tl for w in ["search", "research", "find", "web"]):
                mapping[task] = ["agentgpt"]
            elif any(w in tl for w in ["coordinate", "team", "multi", "crew"]):
                mapping[task] = ["crewai"]
            elif any(w in tl for w in ["parallel", "scale", "swarm", "distribute"]):
                mapping[task] = ["iswarmsai"]
            else:
                mapping[task] = ["agentgpt", "agent_k"]
        return mapping
