"""
Base interface for agent framework adapters.

Every adapter implements AgentFramework so callers never need to know
whether they're talking to CrewAI, Swarms, or something else.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    """Specification for creating an agent inside a framework."""
    name: str
    role: str
    goal: str
    backstory: str = ""
    tools: List[Any] = field(default_factory=list)
    llm_model: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskSpec:
    """Specification for a task to assign to agents."""
    description: str
    expected_output: str = ""
    agent_name: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """Result returned after running agents on tasks."""
    output: str
    raw: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentFramework(ABC):
    """Abstract base for agent framework adapters.

    Mirrors the pattern in frameworks/llm/multi_llm.py — each backend
    implements a small set of methods and the rest of the system programs
    against this interface.
    """

    @abstractmethod
    def add_agent(self, spec: AgentSpec) -> None:
        """Register an agent from a spec."""

    @abstractmethod
    def run(self, tasks: List[TaskSpec], **kwargs) -> RunResult:
        """Execute tasks using the registered agents. Blocking call."""

    @abstractmethod
    def available(self) -> bool:
        """Return True if the underlying library is importable."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this backend (e.g. 'crewai')."""
