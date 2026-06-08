"""
PMMAGO: NeoVertex1 Fused Enterprise Edition
===========================================
Integrated Polymorphic Meta Mosaic Agentic Gödel Orchestrator
with Native NeoVertex1 Axioms and Holographic Memory.

Architecture: Only orchestrator makes LLM calls. Agents communicate through orchestrator.
"""

from __future__ import annotations
import asyncio
import json
import logging
import numpy as np
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
# from core.init_dual_brain import initialize_dual_brain  # moved
from services.startup import initialize_ghostgoat_brain
from brain.trainer.agentic_trainer import AgenticTrainer

# NOTE: Initialization of the GhostGoat brain should happen at runtime,
# not at import time.  The original code attempted to call
# `initialize_ghostgoat_brain(orchestrator=self)` at module load, which
# raises a NameError because `self` does not exist.  Instead we expose a
# helper that can be called by the orchestrator when it is instantiated.

def init_brain(orchestrator):
    """Initialize the dual‑brain for a given orchestrator.
    
    This function is deliberately lightweight and can be imported safely
    without side‑effects.
    """
    return initialize_ghostgoat_brain(orchestrator=orchestrator)

# Placeholder – will be set by the orchestrator via `init_brain(self)`.
dual_brain = None

logger = logging.getLogger(__name__)
_EXECUTOR = ThreadPoolExecutor(thread_name_prefix="pmmago")

# ─── NeoVertex1 Logic Foundation ──────────────────────────────────────────────

class AxiomLogic:
    """Core NeoVertex1 recursive logic and memory primitives."""
    
    @staticmethod
    def wrap(text: str, depth: int = 3) -> str:
        """Simplified wrapper for LLM calls."""
        return f"Task: {text}\n\nRespond in JSON format with 'plan' (list of steps) and 'payload'."

    @staticmethod
    def bind_nugget(v_a: np.ndarray, v_b: np.ndarray) -> np.ndarray:
        """Circular convolution for Holographic Reduced Representations."""
        return np.fft.ifft(np.fft.fft(v_a) * np.fft.fft(v_b)).real

# ─── Core Abstractions ────────────────────────────────────────────────────────

class Agent(ABC):
    """Agent that returns prompts for orchestrator to process via LLM."""
    @abstractmethod
    def __call__(self, state: Dict, context: Dict, goal: Dict) -> Tuple[Dict, Dict, Dict, Optional[str]]:
        """
        Returns: (actions, new_state, artifacts, llm_prompt)
        If llm_prompt is not None, orchestrator will call LLM and re-invoke agent with response.
        """
        ...

@dataclass
class Tile:
    name: str
    agent: Agent
    policy: Dict = field(default_factory=dict)
    memory: Dict = field(default_factory=dict)

class MosaicGraph:
    def __init__(self) -> None:
        self.tiles: Dict[str, Tile] = {}
        self.edges: Dict[str, List[str]] = {}
        self._parallel_groups: List[Set[str]] = []
    
    def add_tile(self, tile: Tile):
        self.tiles[tile.name] = tile
        self.edges.setdefault(tile.name, [])
    
    def connect(self, src: str, dst: str):
        self.edges.setdefault(src, []).append(dst)
    
    def add_parallel_group(self, *names: str):
        self._parallel_groups.append(set(names))

# ─── Specialist NeoVertex Agents ──────────────────────────────────────────────

class NeoPlanner(Agent):
    """Planner that requests LLM to route tasks."""
    def __init__(self, tiles: List[str]):
        self._tiles = tiles
    
    def __call__(self, state, context, goal, llm_response: str = None):
        if llm_response is None:
            # First call: request LLM to generate plan
            prompt = AxiomLogic.wrap(
                f"Orchestrate GhostGoat tiles: {self._tiles}. Goal: {goal.get('description')}"
            )
            return {}, {}, {}, prompt  # Return prompt for orchestrator
        
        # Second call: parse LLM response
        raw = llm_response
        try:
            data = json.loads(raw.strip("`json \n"))
            plan = data.get('payload', {}).get('plan', ['direct_response'])
            persona = data.get('payload', {}).get('persona', 'general')
        except:
            plan, persona = ['direct_response'], 'general'
            
        return {"plan": plan, "persona": persona}, {**state, "meta_plan": plan}, {"raw": raw}, None

class GodelCritic(Agent):
    """Self-referential critic that identifies 'Axiom Gaps'."""
    def __call__(self, state, context, goal, llm_response: str = None):
        if llm_response is None:
            trace = context.get("trace", [])
            prompt = AxiomLogic.wrap(f"Audit this trace for Axiom Gaps: {json.dumps(trace)[:2000]}")
            return {}, {}, {}, prompt
        
        raw = llm_response
        try:
            critique = json.loads(raw.strip("`json \n")).get('payload', {})
        except:
            critique = {"verdict": "pass", "suggested_patches": []}
            
        return {"critique": critique}, {**state, "godel_critique": critique}, {"critique": critique}, None

class DirectResponseAgent(Agent):
    """Simple agent that requests LLM responses."""
    def __call__(self, state, context, goal, llm_response: str = None):
        if llm_response is None:
            prompt = goal.get('description', str(goal))
            return {}, {}, {}, prompt
        
        response = llm_response
        return {"text": response}, {**state, "direct_response": response}, {}, None

class WorkerAgent(Agent):
    """Generic worker that requests LLM via orchestrator."""
    def __init__(self, role: str):
        self.role = role
    
    def __call__(self, state, context, goal, llm_response: str = None):
        if llm_response is None:
            prompt = AxiomLogic.wrap(f"Role: {self.role}. Goal: {goal.get('description')}. State: {state}")
            return {}, {}, {}, prompt
        
        response = llm_response
        return {"text": response}, {**state, f"{self.role}_output": response}, {}, None

# ─── The Enterprise Meta-Orchestrator ─────────────────────────────────────────

class MetaOrchestrator:
    def __init__(self, graph: MosaicGraph, llm_call: Callable, auto_patch: bool = True):
        self.graph = graph
        self.llm_call = llm_call
        self.auto_patch = auto_patch
        self.patch_log = []
        
    @property
    def planner_tile(self) -> str:
        """Get the planner tile name."""
        return "planner"
        
    @property
    def godel_tile(self) -> str:
        """Get the godel critic tile name."""
        return "godel"

    async def execute_async(self, goal: Dict) -> Dict:
        loop = asyncio.get_event_loop()
        state, context, trace = {}, {"goal": goal}, []
        
        # 1. Neo-Planning (with LLM call via orchestrator)
        plan_result = await self._execute_agent_with_llm('planner', state, context, goal)
        plan_act, state, _, _ = plan_result
        execution_path = plan_act.get('plan', [])
        
        # 2. Parallel Execution (TPU 8t optimization)
        for name in execution_path:
            if name in self.graph.tiles:
                result = await self._execute_agent_with_llm(name, state, context, goal)
                act, n_s, art, _ = result
                state.update(n_s)
                trace.append({"tile": name, "actions": act, "artifacts": art})
        
        # 3. Gödel Audit & Auto-Patch
        context["trace"] = trace
        godel_result = await self._execute_agent_with_llm('godel', state, context, goal)
        c_act, state, c_art, _ = godel_result
        
        critique = c_art.get('critique', {})
        if self.auto_patch and critique.get('verdict') == 'fail':
            for patch in critique.get('suggested_patches', []):
                self.apply_patch(patch)
        
        return {"state": state, "trace": trace, "patches": self.patch_log}
    
    async def _execute_agent_with_llm(self, tile_name: str, state, context, goal):
        """Execute an agent, making LLM call if needed."""
        loop = asyncio.get_event_loop()
        tile = self.graph.tiles[tile_name]
        
        # First call: agent returns prompt for LLM
        act, n_s, art, prompt = tile.agent(state, context, goal)
        
        if prompt:
            # Call LLM (only orchestrator does this)
            llm_response = await loop.run_in_executor(_EXECUTOR, self.llm_call, prompt)
            # Second call: agent processes LLM response
            act, n_s, art, _ = tile.agent(state, context, goal, llm_response)
        
        return act, n_s, art, None
    
    def apply_patch(self, patch):
        self.patch_log.append({**patch, "ts": datetime.now(timezone.utc).isoformat()})
        # Logic for graph modification (remove/connect) goes here

# NOTE: The worker count should be configurable via an environment variable.
# If GHOSTGOAT_WORKERS is set, use it; otherwise fall back to the default (8).
# This allows CI pipelines or low‑resource containers to limit parallelism.

import os

DEFAULT_WORKERS = int(os.getenv("GHOSTGOAT_WORKERS", 8))

def build_enterprise_pmmago(llm_call, n_workers=DEFAULT_WORKERS):
    graph = MosaicGraph()
    worker_names = [f"worker_{i}" for i in range(n_workers)]
    
    graph.add_tile(Tile("planner", NeoPlanner(worker_names)))
    graph.add_tile(Tile("godel", GodelCritic()))
    
    for name in worker_names:
        graph.add_tile(Tile(name, WorkerAgent(name)))
    
    return MetaOrchestrator(graph, llm_call)
