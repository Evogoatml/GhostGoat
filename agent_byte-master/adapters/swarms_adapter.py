"""
Swarms adapter — wraps the swarms pip package.

Install:  pip install swarms swarm-models
Docs:     https://docs.swarms.world

Usage through the adapter:

    from frameworks.agents.swarms_adapter import SwarmsFramework
    fw = SwarmsFramework()
    fw.add_agent(AgentSpec(name="analyst", role="Data Analyst",
                           goal="Analyze datasets", llm_model="gpt-4"))
    result = fw.run([TaskSpec(description="Summarize Q4 revenue data")])
    print(result.output)
"""

import logging
from typing import Any, Dict, List, Optional

from frameworks.agents.base import AgentFramework, AgentSpec, RunResult, TaskSpec

logger = logging.getLogger(__name__)

_HAS_SWARMS = False
try:
    from swarms import Agent as SwarmAgent
    _HAS_SWARMS = True
except ImportError:
    pass


class SwarmsFramework(AgentFramework):
    """Thin adapter over the swarms library."""

    def __init__(self, max_loops: int = 1):
        """
        Args:
            max_loops: Default max reasoning loops per agent.
        """
        self._max_loops = max_loops
        self._agents: Dict[str, Any] = {}  # name -> swarms.Agent

    # -- AgentFramework interface ------------------------------------------

    def available(self) -> bool:
        return _HAS_SWARMS

    def name(self) -> str:
        return "swarms"

    def add_agent(self, spec: AgentSpec) -> None:
        if not _HAS_SWARMS:
            raise RuntimeError("swarms is not installed. Run: pip install swarms")

        system_prompt = (
            f"You are {spec.role}.\n"
            f"Goal: {spec.goal}\n"
        )
        if spec.backstory:
            system_prompt += f"Background: {spec.backstory}\n"

        kwargs: Dict[str, Any] = {
            "agent_name": spec.name,
            "system_prompt": system_prompt,
            "max_loops": self._max_loops,
        }
        if spec.llm_model:
            kwargs["model_name"] = spec.llm_model
        if spec.tools:
            kwargs["tools"] = spec.tools
        kwargs.update(spec.extra)

        agent = SwarmAgent(**kwargs)
        self._agents[spec.name] = agent
        logger.debug("Swarms agent registered: %s", spec.name)

    def run(self, tasks: List[TaskSpec], **kwargs) -> RunResult:
        if not _HAS_SWARMS:
            raise RuntimeError("swarms is not installed. Run: pip install swarms")
        if not self._agents:
            raise ValueError("No agents registered — call add_agent() first")

        outputs: List[str] = []
        for ts in tasks:
            agent = self._resolve_agent(ts.agent_name)
            prompt = ts.description
            if ts.expected_output:
                prompt += f"\n\nExpected output format: {ts.expected_output}"
            raw = agent.run(prompt)
            outputs.append(str(raw))

        combined = "\n---\n".join(outputs)
        return RunResult(
            output=combined,
            raw=outputs,
            metadata={"framework": "swarms", "task_count": len(tasks)},
        )

    # -- helpers -----------------------------------------------------------

    def _resolve_agent(self, agent_name: Optional[str]) -> Any:
        """Return the swarms Agent for a given name, or the first registered one."""
        if agent_name and agent_name in self._agents:
            return self._agents[agent_name]
        if agent_name:
            logger.warning("Agent '%s' not found, falling back to first agent", agent_name)
        return next(iter(self._agents.values()))
