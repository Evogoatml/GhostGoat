"""
LangGraph adapter — wraps langgraph's StateGraph.

Install:  pip install langgraph
Docs:     https://langchain-ai.github.io/langgraph/

Key design choices
------------------
* Uses langgraph for **workflow control** only (graph topology, checkpointing,
  human-interrupt gates).  Does NOT use LangChain LLM abstractions — all LLM
  calls go through GhostGoat's own MultiLLM layer.
* Implements the same AgentFramework ABC as CrewAI/Swarms adapters, so callers
  never need to know which backend they're using.
* Each registered agent becomes a StateGraph node.  Tasks flow through nodes
  in the order they are submitted (or via conditional edges if provided).
* Supports optional MemorySaver checkpointing for crash-recovery, and an
  optional human-interrupt node to replace fragile input() calls.

Usage
-----
    from frameworks.agents.langgraph_adapter import LangGraphFramework
    from frameworks.agents.base import AgentSpec, TaskSpec

    fw = LangGraphFramework(checkpointing=True)
    fw.add_agent(AgentSpec(
        name="analyst",
        role="Security Analyst",
        goal="Triage alerts",
        extra={"node_fn": my_custom_fn},   # optional — see below
    ))
    result = fw.run([TaskSpec(description="Analyse CVE-2024-12345")])
    print(result.output)

Custom node functions
---------------------
Each agent node calls ``spec.extra.get("node_fn")``.  The callable receives the
current GraphState dict and must return an updated GraphState dict.  If no
``node_fn`` is provided the adapter uses a built-in stub that records the task
description as output (useful for wiring up and testing the graph shape).

Human-interrupt gate
--------------------
    fw = LangGraphFramework(human_interrupt_node="analyst")

The graph will pause before the named node and emit an ``interrupt_data`` entry
in the state.  Resume by calling ``fw.resume(state, answer)`` with the external
decision.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, TypedDict

from frameworks.agents.base import AgentFramework, AgentSpec, RunResult, TaskSpec

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional langgraph import
# ---------------------------------------------------------------------------
_HAS_LANGGRAPH = False
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    _HAS_LANGGRAPH = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Shared graph state schema
# ---------------------------------------------------------------------------

class GraphState(TypedDict, total=False):
    """Mutable state threaded through every node in the workflow graph."""
    pending_tasks: List[Dict[str, Any]]   # TaskSpec dicts not yet processed
    results: List[str]                    # accumulated per-node outputs
    interrupt_data: Optional[Dict]        # set when a human-interrupt fires
    error: Optional[str]                  # last error message


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class LangGraphFramework(AgentFramework):
    """
    Thin adapter over langgraph.StateGraph.

    Parameters
    ----------
    checkpointing : bool
        If True, attach a MemorySaver so graphs survive process restarts.
    human_interrupt_node : str | None
        Name of the agent node before which the graph should pause for human
        approval.  Resume with ``fw.resume(state, answer)``.
    """

    def __init__(
        self,
        checkpointing: bool = False,
        human_interrupt_node: Optional[str] = None,
    ):
        self._checkpointing = checkpointing
        self._human_interrupt_node = human_interrupt_node
        self._specs: Dict[str, AgentSpec] = {}          # name -> AgentSpec
        self._node_order: List[str] = []                # insertion order

    # ------------------------------------------------------------------
    # AgentFramework interface
    # ------------------------------------------------------------------

    def available(self) -> bool:
        return _HAS_LANGGRAPH

    def name(self) -> str:
        return "langgraph"

    def add_agent(self, spec: AgentSpec) -> None:
        if not _HAS_LANGGRAPH:
            raise RuntimeError(
                "langgraph is not installed.  Run: pip install langgraph"
            )
        self._specs[spec.name] = spec
        if spec.name not in self._node_order:
            self._node_order.append(spec.name)
        logger.debug("LangGraph agent registered: %s", spec.name)

    def run(self, tasks: List[TaskSpec], **kwargs) -> RunResult:
        if not _HAS_LANGGRAPH:
            raise RuntimeError(
                "langgraph is not installed.  Run: pip install langgraph"
            )
        if not self._specs:
            raise ValueError("No agents registered — call add_agent() first")

        graph = self._build_graph()
        initial_state: GraphState = {
            "pending_tasks": [
                {
                    "description": t.description,
                    "expected_output": t.expected_output,
                    "agent_name": t.agent_name,
                    "context": t.context,
                }
                for t in tasks
            ],
            "results": [],
            "interrupt_data": None,
            "error": None,
        }

        thread_id = kwargs.pop("thread_id", str(uuid.uuid4()))
        config = {"configurable": {"thread_id": thread_id}}

        final_state = graph.invoke(initial_state, config=config, **kwargs)

        output = "\n---\n".join(final_state.get("results", []))
        return RunResult(
            output=output,
            raw=final_state,
            metadata={
                "framework": "langgraph",
                "thread_id": thread_id,
                "task_count": len(tasks),
                "checkpointing": self._checkpointing,
            },
        )

    # ------------------------------------------------------------------
    # Human-interrupt resume
    # ------------------------------------------------------------------

    def resume(self, thread_id: str, answer: Any) -> RunResult:
        """Resume a graph that paused at the human-interrupt node.

        Args:
            thread_id: The thread_id that was returned in RunResult.metadata.
            answer:    The human decision / input to inject into the state.
        """
        if not _HAS_LANGGRAPH:
            raise RuntimeError("langgraph is not installed.")

        graph = self._build_graph()
        config = {"configurable": {"thread_id": thread_id}}

        # Inject the answer into state by resuming via None input + state patch
        final_state = graph.invoke(
            {"interrupt_data": {"answer": answer, "resolved": True}},
            config=config,
        )
        output = "\n---\n".join(final_state.get("results", []))
        return RunResult(
            output=output,
            raw=final_state,
            metadata={"framework": "langgraph", "thread_id": thread_id, "resumed": True},
        )

    # ------------------------------------------------------------------
    # Internal graph construction
    # ------------------------------------------------------------------

    def _build_graph(self):
        """Compile a fresh StateGraph from registered agents."""
        builder = StateGraph(GraphState)

        for agent_name in self._node_order:
            spec = self._specs[agent_name]
            node_fn = self._make_node(agent_name, spec)

            if agent_name == self._human_interrupt_node and _HAS_LANGGRAPH:
                # Wrap with interrupt gate
                node_fn = self._wrap_with_interrupt(agent_name, node_fn)

            builder.add_node(agent_name, node_fn)

        # Wire nodes sequentially: start -> node0 -> node1 -> ... -> END
        if self._node_order:
            builder.set_entry_point(self._node_order[0])
            for i in range(len(self._node_order) - 1):
                builder.add_edge(self._node_order[i], self._node_order[i + 1])
            builder.add_edge(self._node_order[-1], END)
        else:
            builder.set_entry_point(END)

        checkpointer = MemorySaver() if self._checkpointing else None
        return builder.compile(checkpointer=checkpointer)

    def _make_node(
        self, agent_name: str, spec: AgentSpec
    ) -> Callable[[GraphState], GraphState]:
        """Return the node function for an agent.

        If ``spec.extra["node_fn"]`` is provided it is used as-is.
        Otherwise a built-in stub records the task and continues.
        """
        custom_fn: Optional[Callable] = spec.extra.get("node_fn")

        def _node(state: GraphState) -> GraphState:
            if custom_fn is not None:
                return custom_fn(state)

            # --- built-in stub -------------------------------------------
            # Find the first pending task assigned to (or not yet claimed by)
            # this agent and consume it.
            pending = list(state.get("pending_tasks", []))
            target = None
            remaining = []
            for t in pending:
                if target is None and (
                    t.get("agent_name") == agent_name or t.get("agent_name") is None
                ):
                    target = t
                else:
                    remaining.append(t)

            if target is None and pending:
                # fallback: take the first task
                target, remaining = pending[0], pending[1:]

            if target:
                output = (
                    f"[{agent_name} | {spec.role}] "
                    f"processed: {target['description']}"
                )
            else:
                output = f"[{agent_name} | {spec.role}] no task assigned"

            return {
                **state,
                "pending_tasks": remaining,
                "results": list(state.get("results", [])) + [output],
            }

        _node.__name__ = agent_name
        return _node

    def _wrap_with_interrupt(
        self, agent_name: str, inner_fn: Callable
    ) -> Callable[[GraphState], GraphState]:
        """Wrap a node with a human-interrupt gate using langgraph interrupt()."""
        try:
            from langgraph.types import interrupt as lg_interrupt
        except ImportError:
            # Older langgraph — interrupt not available, skip wrapping
            logger.warning(
                "langgraph.types.interrupt not available; "
                "skipping human-interrupt gate for node %s",
                agent_name,
            )
            return inner_fn

        def _gated_node(state: GraphState) -> GraphState:
            resolved = (state.get("interrupt_data") or {}).get("resolved", False)
            if not resolved:
                # Pause graph and surface the current pending task to the human
                pending = state.get("pending_tasks", [])
                question = (
                    f"Human approval required before node '{agent_name}'.\n"
                    f"Next task: {pending[0] if pending else 'none'}\n"
                    f"Approve? (yes/no/edit)"
                )
                answer = lg_interrupt(question)
                # After resume, answer is injected into state by the caller
                if str(answer).strip().lower() in ("no", "cancel", "reject"):
                    return {
                        **state,
                        "error": f"Task rejected by human at node '{agent_name}'",
                    }
            return inner_fn(state)

        _gated_node.__name__ = f"{agent_name}_gated"
        return _gated_node
