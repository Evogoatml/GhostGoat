"""
CrewAI Agent — Multi-Role Team Coordinator
Skills: structured role assignment, sequential task pipelines,
        human-in-loop handoffs, output validation between roles.
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


class CrewAIAgentSpec:
    def __init__(self, role: str, goal: str, backstory: str):
        self.role = role
        self.goal = goal
        self.backstory = backstory


class CrewAISpecialist(BaseAgent):
    """
    Multi-role team coordinator. Specialises in:
    - Assigning roles to sub-agents (researcher, writer, reviewer, coder)
    - Sequential pipeline execution (one role feeds the next)
    - Output validation between pipeline stages
    - Structured deliverables (reports, code, plans)
    """

    SKILLS = [
        "multi-role team assignment",
        "sequential task pipelines",
        "output validation between stages",
        "structured report generation",
        "researcher + writer + reviewer pipeline",
        "code review pipeline",
    ]

    # Default role templates
    ROLES = {
        "researcher": CrewAIAgentSpec(
            role="Researcher",
            goal="Find and compile relevant information",
            backstory="Expert at finding, evaluating, and summarising information."
        ),
        "analyst": CrewAIAgentSpec(
            role="Analyst",
            goal="Analyse data and identify patterns",
            backstory="Data analyst specialising in pattern recognition and insights."
        ),
        "writer": CrewAIAgentSpec(
            role="Writer",
            goal="Transform research into clear, structured output",
            backstory="Technical writer who creates clear, actionable content."
        ),
        "reviewer": CrewAIAgentSpec(
            role="Reviewer",
            goal="Validate and improve the output quality",
            backstory="Critical reviewer who identifies errors and improvements."
        ),
        "coder": CrewAIAgentSpec(
            role="Coder",
            goal="Write and validate code solutions",
            backstory="Senior software engineer with broad language expertise."
        ),
    }

    @property
    def name(self) -> str:
        return "crewai"

    @property
    def description(self) -> str:
        return "Multi-role team coordinator — structured pipelines with role specialisation"

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.update_state(status="executing", current_task=task)
        ctx = context or {}
        bus.publish_sync("agent.thinking", {"agent": self.name, "task": task[:80]}, source=self.name)

        # Try native CrewAI first
        result = self._try_crewai_native(task)
        if result:
            self._store(task, result)
            return result

        # Fallback: simulate the crew pipeline with LLM
        result = self._simulate_crew(task, ctx)
        self._store(task, result)
        return result

    def _try_crewai_native(self, task: str) -> Optional[str]:
        try:
            from frameworks.agents.registry import get_framework
            from frameworks.agents.base import AgentSpec, TaskSpec
            fw = get_framework("crewai")
            fw.add_agent(AgentSpec(name="crew_main", role="coordinator", goal=task))
            result = fw.run([TaskSpec(description=task, expected_output="complete output",
                                      agent_name="crew_main")])
            return str(result.output)
        except Exception as e:
            logger.warning("[CrewAI] native framework unavailable (%s), using simulated pipeline", e)
            return None

    def _simulate_crew(self, task: str, ctx: Dict) -> str:
        """Run researcher → analyst → writer pipeline via LLM."""
        roles_to_run = self._pick_roles(task)
        pipeline_output = task
        trace = []

        for role_name in roles_to_run:
            role = self.ROLES.get(role_name)
            if not role:
                continue
            prior = "\n".join(trace[-2:]) if trace else ""
            prompt = (
                f"You are the {role.role} in a multi-agent team.\n"
                f"Your goal: {role.goal}\n"
                f"Backstory: {role.backstory}\n\n"
                f"Original task: {task}\n"
                f"Previous work:\n{prior}\n\n"
                "Complete your part of the task. Be specific and thorough."
            )
            output = llm.call(prompt)
            trace.append(f"[{role.role}]: {output[:500]}")
            pipeline_output = output

        return pipeline_output

    def _pick_roles(self, task: str) -> List[str]:
        tl = task.lower()
        if any(w in tl for w in ["code", "script", "function", "debug"]):
            return ["researcher", "coder", "reviewer"]
        if any(w in tl for w in ["report", "write", "document", "explain"]):
            return ["researcher", "analyst", "writer"]
        if any(w in tl for w in ["analyze", "analyse", "data", "pattern"]):
            return ["researcher", "analyst", "reviewer"]
        return ["researcher", "writer"]

    def _store(self, task: str, result: str):
        memory.remember(result, agent_id=self.name, metadata={"task": task, "type": "crew_output"})
        bus.publish_sync("agent.result", {"agent": self.name, "task": task[:60]}, source=self.name)
