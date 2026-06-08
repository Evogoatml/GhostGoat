"""
AgentGPT Agent — Autonomous Web Researcher & Planner
Skills: web search, URL fetching, iterative research loops,
        knowledge synthesis, fact verification.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from core.controllers.memory_controller import memory
from core.controllers.llm_controller import llm
from core.bridges.search_bridge import search_bridge
from core.bus.agent_bus import bus
from core.init_dual_brain import initialize_dual_brain

# At startup
dual_brain = initialize_dual_brain(orchestrator=your_orchestrator)

logger = logging.getLogger(__name__)


class AgentGPTAgent(BaseAgent):
    """
    Autonomous researcher. Specialises in:
    - Web search and URL fetching
    - Iterative research (search → read → refine → repeat)
    - Knowledge synthesis across sources
    - Fact verification
    - Generating structured research reports
    """

    SKILLS = [
        "web search",
        "iterative research loops",
        "URL content fetching",
        "knowledge synthesis",
        "fact verification",
        "research report generation",
    ]

    @property
    def name(self) -> str:
        return "agentgpt"

    @property
    def description(self) -> str:
        return "Autonomous researcher — web search, synthesis, and iterative information gathering"

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.update_state(status="executing", current_task=task)
        ctx = context or {}
        bus.publish_sync("agent.thinking", {"agent": self.name, "task": task[:80]}, source=self.name)

        # Check if we already know this
        recalled = memory.recall(task, agent_id=self.name, k=3)
        if recalled and recalled[0].get("distance", 1.0) < 0.15:
            logger.info("[AgentGPT] memory hit for: %s", task[:40])
            return recalled[0]["content"]

        # Research loop: search → read → synthesise
        search_query = self._build_query(task, ctx)
        search_results = search_bridge.search(search_query, num_results=5)

        if not search_results:
            # No search results — LLM direct
            return self._llm_direct(task, ctx, [])

        synthesis = self._synthesise(task, search_results, ctx)

        # Store for future recall
        memory.remember(synthesis, agent_id=self.name,
                        metadata={"task": task, "type": "research_result",
                                  "sources": [r.get("url","") for r in search_results[:3]]})
        bus.publish_sync("agent.result", {"agent": self.name, "task": task[:60],
                                           "sources": len(search_results)}, source=self.name)
        return synthesis

    def _build_query(self, task: str, ctx: Dict) -> str:
        prompt = (
            f"Convert this task into the best web search query (max 10 words):\n{task}\n\n"
            "Return ONLY the search query, nothing else."
        )
        return llm.call(prompt).strip().strip('"')

    def _synthesise(self, task: str, results: List[Dict], ctx: Dict) -> str:
        snippets = "\n\n".join(
            f"[{r.get('title','')}] {r.get('snippet','')}" for r in results[:5]
        )
        prompt = (
            f"Task: {task}\n\n"
            f"Search results:\n{snippets}\n\n"
            "Synthesise the information above into a clear, complete answer to the task. "
            "Cite sources where relevant."
        )
        return llm.call(prompt)

    def _llm_direct(self, task: str, ctx: Dict, results: List) -> str:
        recalled = memory.recall(task, k=3)
        context_str = "\n".join(r["content"][:200] for r in recalled)
        prompt = (
            f"Task: {task}\n"
            f"Relevant context from memory:\n{context_str}\n\n"
            "Answer this task thoroughly."
        )
        return llm.call(prompt)
