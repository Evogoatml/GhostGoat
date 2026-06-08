"""
NLM Layer — Unified Multi-Agent Team (overseen by PMMAGO)
===========================================================

Sits between the PMMAGO Multi-Agent Layer and the framework backends.

Architecture position
---------------------
  Telegram/LLM
       ↓
  PMMAGO (Mosaic · Agentic · Gödel · Meta · Adaptive)
       ↓
  NLM Layer  ← you are here
       ↓
  Agent K · SuperAGI · CrewAI · AgentGPT · iSwarmsAI

Team model (not fan-out)
------------------------
Agents work as a unified team sharing a common TeamState.  Each agent
reads what the previous agents produced, adds its own contribution, and
passes the enriched state forward.  A Synthesiser agent at the end merges
all contributions into one coherent answer.  The Gödel critic (from PMMAGO)
then validates the team's output.

Message envelope (code agents pass between themselves)::

    {
        "id":           "<uuid>",
        "task":         "<original task>",
        "domain":       "<semantic route>",
        "team_state":   { agent_name: contribution, ... },
        "context":      { ...caller context + pmmago result... },
        "round":        <int>,
        "final_output": null | "<synthesised answer>"
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Persona-aware routing (imported lazily to avoid circular imports at module load)
def _get_persona(domain: str):
    try:
        from core.brain.agents.personas import get_persona
        return get_persona(domain)
    except Exception:
        return None

_EXECUTOR = ThreadPoolExecutor(thread_name_prefix="nlm_team")


# ── Shared team state ─────────────────────────────────────────────────────────

@dataclass
class TeamState:
    """Shared mutable state passed through the agent team."""
    task: str
    domain: str
    context: Dict[str, Any] = field(default_factory=dict)
    contributions: Dict[str, str] = field(default_factory=dict)  # agent -> output
    errors: Dict[str, str] = field(default_factory=dict)
    final_output: Optional[str] = None
    round: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_code(self) -> str:
        return json.dumps({
            "id": self.id,
            "task": self.task,
            "domain": self.domain,
            "team_state": self.contributions,
            "context": self.context,
            "round": self.round,
            "final_output": self.final_output,
            "created_at": self.created_at,
        }, default=str)

    @classmethod
    def from_code(cls, code: str) -> "TeamState":
        d = json.loads(code)
        s = cls(task=d["task"], domain=d["domain"])
        s.id = d.get("id", s.id)
        s.context = d.get("context", {})
        s.contributions = d.get("team_state", {})
        s.round = d.get("round", 0)
        s.final_output = d.get("final_output")
        s.created_at = d.get("created_at", s.created_at)
        return s

    def team_summary(self, exclude: Optional[str] = None) -> str:
        """Return a human-readable summary of all contributions so far."""
        parts = []
        for agent, output in self.contributions.items():
            if agent != exclude and output:
                parts.append(f"[{agent}]: {output[:400]}")
        return "\n".join(parts) if parts else "No contributions yet."


# ── Base team agent ───────────────────────────────────────────────────────────

class TeamAgent:
    """
    Base class for all NLM team members.

    Each agent:
    1. Reads the shared TeamState (sees what teammates already did)
    2. Adds its own contribution
    3. Returns the updated TeamState as a code string
    """
    name: str = "base"
    role: str = "worker"

    def handle(self, code: str) -> str:
        try:
            state = TeamState.from_code(code)
            contribution = self._contribute(state)
            state.contributions[self.name] = contribution
            state.round += 1
        except Exception as exc:
            logger.warning("[%s] failed: %s", self.name, exc)
            try:
                state = TeamState.from_code(code)
            except Exception:
                state = TeamState(task="unknown", domain="unknown")
            state.errors[self.name] = str(exc)
            state.contributions[self.name] = ""
        return state.to_code()

    def _contribute(self, state: TeamState) -> str:
        raise NotImplementedError


# ── Team members ──────────────────────────────────────────────────────────────

class AgentKTeamMember(TeamAgent):
    """Agent K — skill library specialist. Looks up known solutions first."""
    name = "agent_k"
    role = "skill_specialist"

    def _contribute(self, state: TeamState) -> str:
        try:
            from core.brain.agents import tool_agent as skill_library
            result = skill_library.execute(state.task, context=state.context)
            return str(result)
        except Exception as exc:
            return f"No stored skill matched. Suggestion: {state.task} — {exc}"


class CrewAITeamMember(TeamAgent):
    """CrewAI — multi-role collaborative executor."""
    name = "crewai"
    role = "executor"

    def _contribute(self, state: TeamState) -> str:
        from frameworks.agents.registry import get_framework
        from frameworks.agents.base import AgentSpec, TaskSpec
        # Enrich task with what teammates already found
        enriched = state.task
        prior = state.team_summary(exclude=self.name)
        if prior:
            enriched = f"{state.task}\n\nTeam context so far:\n{prior}"
        fw = get_framework("crewai")
        fw.add_agent(AgentSpec(name="crewai_exec", role="executor", goal=enriched))
        result = fw.run([TaskSpec(description=enriched, expected_output="task output",
                                  agent_name="crewai_exec")])
        return str(result.output)


class SwarmsTeamMember(TeamAgent):
    """iSwarmsAI — distributed swarm executor."""
    name = "iswarmsai"
    role = "swarm_executor"

    def _contribute(self, state: TeamState) -> str:
        from frameworks.agents.registry import get_framework
        from frameworks.agents.base import AgentSpec, TaskSpec
        enriched = state.task
        prior = state.team_summary(exclude=self.name)
        if prior:
            enriched = f"{state.task}\n\nTeam context:\n{prior}"
        fw = get_framework("swarms")
        fw.add_agent(AgentSpec(name="swarms_exec", role="executor", goal=enriched))
        result = fw.run([TaskSpec(description=enriched, expected_output="task output",
                                  agent_name="swarms_exec")])
        return str(result.output)


class AgentGPTTeamMember(TeamAgent):
    """AgentGPT/LangGraph — autonomous task planner and executor."""
    name = "agentgpt"
    role = "planner_executor"

    def _contribute(self, state: TeamState) -> str:
        from frameworks.agents.registry import get_framework
        from frameworks.agents.base import AgentSpec, TaskSpec
        enriched = state.task
        prior = state.team_summary(exclude=self.name)
        if prior:
            enriched = f"{state.task}\n\nTeam context:\n{prior}"
        fw = get_framework("langgraph")
        fw.add_agent(AgentSpec(name="lg_exec", role="planner", goal=enriched))
        result = fw.run([TaskSpec(description=enriched, expected_output="task output",
                                  agent_name="lg_exec")])
        return str(result.output)


class SuperAGITeamMember(TeamAgent):
    """SuperAGI — autonomous goal decomposer."""
    name = "superagi"
    role = "goal_decomposer"

    def __init__(self, llm_call=None):
        self._llm = llm_call

    def _contribute(self, state: TeamState) -> str:
        prior = state.team_summary(exclude=self.name)
        persona = _get_persona(state.domain)
        persona_ctx = f"\n\n{persona.system_prompt}" if persona else ""
        prompt = (
            f"You are an autonomous goal-decomposer working in a specialist AI team.{persona_ctx}\n\n"
            f"Task: {state.task}\n"
            f"Domain: {state.domain}\n\n"
            f"What your teammates have contributed so far:\n{prior}\n\n"
            "Add your own analysis, fill gaps, and extend the team's work."
        )
        if self._llm:
            return self._llm(prompt)
        return f"Stub — would decompose: {state.task}"


class SynthesiserAgent(TeamAgent):
    """
    Final team member — reads all contributions and produces one unified answer.
    This is the agent whose output becomes the response to the user.
    """
    name = "synthesiser"
    role = "synthesiser"

    def __init__(self, llm_call=None):
        self._llm = llm_call

    def _contribute(self, state: TeamState) -> str:
        team_work = state.team_summary()
        persona = _get_persona(state.domain)
        persona_ctx = f"\n\n{persona.system_prompt}" if persona else ""
        prompt = (
            f"You are the final synthesiser for a specialist AI team.{persona_ctx}\n\n"
            f"Original task: {state.task}\n\n"
            f"Team contributions:\n{team_work}\n\n"
            "Synthesise all contributions into one clear, complete, unified answer. "
            "Remove duplicates, resolve contradictions, and present the best combined result. "
            "Speak in first person as the specialist persona above."
        )
        if self._llm:
            result = self._llm(prompt)
            state.final_output = result
            return result
        # Fallback: pick the longest non-empty contribution
        best = max(
            (v for v in state.contributions.values() if v),
            key=len,
            default=state.task,
        )
        state.final_output = best
        return best


# ── Domain routing — driven by persona definitions ────────────────────────────

def _build_roster() -> Dict[str, List[str]]:
    """Build the domain→agents roster from persona definitions."""
    try:
        from core.brain.agents.personas import PERSONAS
        roster = {}
        for persona in PERSONAS.values():
            for domain in persona.domains:
                roster[domain] = persona.nlm_agents
        return roster
    except Exception:
        # Hard fallback if personas module unavailable
        return {
            "coding":   ["agent_k", "agentgpt", "synthesiser"],
            "research": ["agentgpt", "superagi", "synthesiser"],
            "creative": ["superagi", "agentgpt", "synthesiser"],
            "planning": ["agentgpt", "crewai", "synthesiser"],
            "analysis": ["agent_k", "agentgpt", "synthesiser"],
            "general":  ["agentgpt", "crewai", "superagi", "synthesiser"],
        }

_TEAM_ROSTER: Dict[str, List[str]] = _build_roster()


# ── NLM Layer ─────────────────────────────────────────────────────────────────

class NLMLayer:
    """
    Unified multi-agent team coordinator.

    Agents run sequentially in role order so each can read what
    the previous agents produced.  The final Synthesiser merges
    all contributions into one coherent answer.

    Parallel agents (same role tier) share a state snapshot and
    their results are merged before the next tier runs.
    """

    # Agents that can run in parallel (they don't depend on each other)
    _PARALLEL_ROLES = {"executor", "goal_decomposer", "planner_executor", "skill_specialist"}

    def __init__(self, llm_call=None):
        self._llm = llm_call
        self._roster: Dict[str, TeamAgent] = {
            "agent_k":    AgentKTeamMember(),
            "crewai":     CrewAITeamMember(),
            "iswarmsai":  SwarmsTeamMember(),
            "agentgpt":   AgentGPTTeamMember(),
            "superagi":   SuperAGITeamMember(llm_call=llm_call),
            "synthesiser": SynthesiserAgent(llm_call=llm_call),
        }

    # ── public API ────────────────────────────────────────────────────────────

    async def dispatch(
        self,
        task: str,
        domain: str = "general",
        context: Optional[Dict[str, Any]] = None,
        pmmago_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the agent team for the given task.
        Returns unified result dict with the synthesised answer.
        """
        ctx = dict(context or {})
        if pmmago_result:
            ctx["pmmago"] = pmmago_result

        state = TeamState(task=task, domain=domain, context=ctx)
        roster = _TEAM_ROSTER.get(domain, _TEAM_ROSTER["general"])

        logger.info("[NLM team] domain=%s roster=%s", domain, roster)

        # Split roster into parallel worker tier + synthesiser
        workers = [n for n in roster if n != "synthesiser" and n in self._roster]
        has_synth = "synthesiser" in roster and "synthesiser" in self._roster

        # Run all workers in parallel (they all start from the same base state
        # snapshot; results are merged into a fresh shared state)
        if workers:
            snap_code = state.to_code()
            loop = asyncio.get_event_loop()
            raw_results = await asyncio.gather(
                *[
                    loop.run_in_executor(_EXECUTOR, self._roster[name].handle, snap_code)
                    for name in workers
                ],
                return_exceptions=True,
            )
            # Merge all worker contributions into state
            for name, raw in zip(workers, raw_results):
                if isinstance(raw, Exception):
                    state.errors[name] = str(raw)
                    logger.warning("[NLM team] %s raised: %s", name, raw)
                else:
                    try:
                        worker_state = TeamState.from_code(raw)
                        contribution = worker_state.contributions.get(name, "")
                        if contribution:
                            state.contributions[name] = contribution
                        state.errors.update(worker_state.errors)
                    except Exception as e:
                        state.errors[name] = str(e)

        # Run synthesiser last — it sees all worker outputs
        if has_synth:
            synth_code = state.to_code()
            loop = asyncio.get_event_loop()
            synth_raw = await loop.run_in_executor(
                _EXECUTOR, self._roster["synthesiser"].handle, synth_code
            )
            try:
                synth_state = TeamState.from_code(synth_raw)
                state.final_output = synth_state.final_output or \
                    synth_state.contributions.get("synthesiser", "")
                state.contributions["synthesiser"] = state.final_output or ""
            except Exception as e:
                logger.warning("[NLM synthesiser] failed: %s", e)

        # Fallback: pick best worker contribution if synthesis failed
        if not state.final_output:
            state.final_output = max(
                (v for v in state.contributions.values() if v),
                key=len,
                default="",
            )

        return {
            "task": task,
            "domain": domain,
            "primary_output": state.final_output,
            "contributions": state.contributions,
            "errors": state.errors,
            "agents_used": list(state.contributions.keys()),
            "success_count": len([v for v in state.contributions.values() if v]),
        }

    # ── PMMAGO tile adapter ───────────────────────────────────────────────────

    def as_pmmago_tile(self, name: str):
        """
        Return this NLMLayer as a PMMAGO-compatible Agent that runs the full
        team and exposes the synthesised result through the tile interface.

        Usage::
            from core.brain.agents.pmmago import Tile
            tile = nlm.as_pmmago_tile("nlm_team")
        """
        nlm = self

        from core.brain.agents.pmmago import Agent as PMMAgent

        class _NLMTeamAgent(PMMAgent):
            def __call__(self_inner, state, context, goal):
                import asyncio
                task = goal.get("description", str(goal))
                domain = goal.get("domain", "general")
                # Carry forward any prior team contributions already in state
                ctx = {**context, "prior_state": state}
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                            result = ex.submit(
                                asyncio.run,
                                nlm.dispatch(task, domain, ctx)
                            ).result()
                    else:
                        result = loop.run_until_complete(
                            nlm.dispatch(task, domain, ctx)
                        )
                except Exception as exc:
                    result = {"primary_output": str(exc), "contributions": {}, "errors": {}}

                actions = {
                    "nlm_output": result["primary_output"],
                    "team_contributions": result.get("contributions", {}),
                }
                new_state = {
                    **state,
                    "nlm_result": result["primary_output"],
                    "nlm_team": result.get("contributions", {}),
                }
                artifacts = {"nlm_full": result}
                return actions, new_state, artifacts

        return _NLMTeamAgent()

    def dispatch_sync(
        self,
        task: str,
        domain: str = "general",
        context: Optional[Dict[str, Any]] = None,
        pmmago_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for non-async callers."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    return ex.submit(
                        asyncio.run,
                        self.dispatch(task, domain, context, pmmago_result)
                    ).result()
            return loop.run_until_complete(
                self.dispatch(task, domain, context, pmmago_result)
            )
        except Exception as exc:
            logger.error("[NLM] dispatch_sync error: %s", exc)
            return {
                "task": task, "domain": domain,
                "primary_output": str(exc),
                "contributions": {}, "errors": {"dispatch": str(exc)},
                "agents_used": [], "success_count": 0,
            }


# ── Factory: PMMAGO + NLM team wired together ─────────────────────────────────

def build_orchestrated_team(
    llm_call,
    auto_patch: bool = True,
) -> "MetaOrchestrator":
    """
    Build a MetaOrchestrator where the NLM unified team runs as a worker tile.

    Graph topology::
        planner → direct_response  (conversational / simple questions)
                → nlm_team         (complex tasks needing agents)
        [Gödel critic post-pass on every run]

    The planner (PMMAGO NeoPlanner) decides what the team should focus on.
    The NLM team (all backends working together) executes and synthesises.
    The Gödel critic (PMMAGO GodelCritic) validates the team's output and can
    trigger auto-patches if the result fails quality checks.
    """
    from core.brain.agents.pmmago import (
        MosaicGraph, Tile, NeoPlanner, GodelCritic, DirectResponseAgent,
        MetaOrchestrator
    )

    nlm = NLMLayer(llm_call=llm_call)
    nlm_agent = nlm.as_pmmago_tile("nlm_team")
    
    graph = MosaicGraph()
    graph.add_tile(Tile(
        "planner",
        NeoPlanner(tiles=["direct_response", "nlm_team"]),
        policy={"role": "planner"},
    ))
    graph.add_tile(Tile(
        "direct_response",
        DirectResponseAgent(),
        policy={"role": "direct"},
    ))
    graph.add_tile(Tile(
        "nlm_team",
        nlm_agent,
        policy={"role": "nlm_unified_team"},
    ))
    graph.add_tile(Tile(
        "godel_critic",
        GodelCritic(),
        policy={"role": "godel"},
    ))
    graph.connect("planner", "direct_response")
    graph.connect("planner", "nlm_team")

    return MetaOrchestrator(
        graph,
        llm_call=llm_call,
        auto_patch=auto_patch,
    )
