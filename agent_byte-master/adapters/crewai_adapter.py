"""
CrewAI adapter — wraps the crewai pip package.

Install:  pip install crewai
Docs:     https://docs.crewai.com

Usage through the adapter:

    from frameworks.agents.crewai_adapter import CrewAIFramework
    fw = CrewAIFramework()
    fw.add_agent(AgentSpec(name="researcher", role="Researcher",
                           goal="Find facts", backstory="Expert analyst"))
    result = fw.run([TaskSpec(description="Summarize recent AI news",
                              agent_name="researcher")])
    print(result.output)
"""

import logging
from typing import Any, Dict, List, Optional

from frameworks.agents.base import AgentFramework, AgentSpec, RunResult, TaskSpec

logger = logging.getLogger(__name__)

_HAS_CREWAI = False
try:
    from crewai import Agent, Crew, Process, Task
    _HAS_CREWAI = True
except ImportError:
    pass


class CrewAIFramework(AgentFramework):
    """Thin adapter over the crewai library."""

    def __init__(self, process: str = "sequential", verbose: bool = False):
        """
        Args:
            process: "sequential" or "hierarchical".
            verbose: Whether crewai agents should log verbosely.
        """
        self._process = process
        self._verbose = verbose
        self._agents: Dict[str, Any] = {}  # name -> crewai.Agent

    # -- AgentFramework interface ------------------------------------------

    def available(self) -> bool:
        return _HAS_CREWAI

    def name(self) -> str:
        return "crewai"

    def add_agent(self, spec: AgentSpec) -> None:
        if not _HAS_CREWAI:
            raise RuntimeError("crewai is not installed. Run: pip install crewai")

        kwargs: Dict[str, Any] = {
            "role": spec.role,
            "goal": spec.goal,
            "backstory": spec.backstory or spec.role,
            "verbose": self._verbose,
        }
        if spec.tools:
            kwargs["tools"] = spec.tools
        if spec.llm_model:
            kwargs["llm"] = spec.llm_model
        kwargs.update(spec.extra)

        agent = Agent(**kwargs)
        self._agents[spec.name] = agent
        logger.debug("CrewAI agent registered: %s", spec.name)

    def run(self, tasks: List[TaskSpec], **kwargs) -> RunResult:
        if not _HAS_CREWAI:
            raise RuntimeError("crewai is not installed. Run: pip install crewai")
        if not self._agents:
            raise ValueError("No agents registered — call add_agent() first")

        crew_tasks = []
        for ts in tasks:
            agent = self._resolve_agent(ts.agent_name)
            task_kwargs: Dict[str, Any] = {
                "description": ts.description,
                "agent": agent,
            }
            if ts.expected_output:
                task_kwargs["expected_output"] = ts.expected_output
            crew_tasks.append(Task(**task_kwargs))

        process = Process.hierarchical if self._process == "hierarchical" else Process.sequential

        crew = Crew(
            agents=list(self._agents.values()),
            tasks=crew_tasks,
            process=process,
            verbose=self._verbose,
            **kwargs,
        )

        raw = crew.kickoff()
        output = str(raw)
        return RunResult(output=output, raw=raw, metadata={"framework": "crewai"})

    # -- helpers -----------------------------------------------------------

    def _resolve_agent(self, agent_name: Optional[str]) -> Any:
        """Return the crewai Agent for a given name, or the first registered one."""
        if agent_name and agent_name in self._agents:
            return self._agents[agent_name]
        if agent_name:
            logger.warning("Agent '%s' not found, falling back to first agent", agent_name)
        return next(iter(self._agents.values()))
