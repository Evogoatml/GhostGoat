#!/usr/bin/env python3
"""GhostGoat orchestrator: the runtime singleton and single source of truth.

Every subsystem is created here, registered in the service registry and shared
by the REST API (``config/api/server.py``), the Telegram bot and the dashboard.
``main.py`` is the only startup entry point; this module only builds and holds
the live state.
"""
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
ABM_ROOT = ROOT / "agent_byte-master"
for _path in (str(ROOT), str(ABM_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from config.api.state_store import RuntimeState
from config.unified_config import UnifiedConfig, get_config

from agents.agent_network import AgentNetwork, ModuleExecutor, set_llm_gateway
from agents.creative_module import CreativeModule
from agents.custom_analyzer import CustomAnalyzerAgent
from brain.dual_brain import DualBrain
from brain.knowledge.knowledge_tank import KnowledgeTank
from core.governance.decision_governor import allow_external_calls
from core.graphrag.engine import GraphRAGEngine
from core.memory.networked_memory import NetworkedMemory
from core.service_registry import registry
from core.workflows.engine import WorkflowEngine
from services.llm_gateway import LLMGateway
from services.sentiment_service import SentimentService
from services.telegram_bot import TelegramBotService

logger = logging.getLogger("ghostgoat.orchestrator")

EventListener = Callable[[Dict[str, Any]], Awaitable[None]]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Orchestrator:
    """One instance owns brain, knowledge, graph, memory, agents, workflows and Telegram."""

    def __init__(self, config: Optional[UnifiedConfig] = None, state_store: Optional[RuntimeState] = None):
        self.config = config or get_config()
        data_dir = Path(self.config.runtime.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        self.started_at = time.time()
        self.running = False
        self.state_store = state_store or RuntimeState(data_dir / "runtime.sqlite3")
        self.governance_log: List[Dict[str, Any]] = []
        self._listeners: List[EventListener] = []

        self.registry = registry
        self.llm = LLMGateway(self.config.llm)
        set_llm_gateway(self.llm)
        self.brain = DualBrain(name="ghostgoat", dimension=128, config={"learning_rate": 0.01})
        self.knowledge_tank = KnowledgeTank(storage_path=str(data_dir / "knowledge_tank"))
        self.graphrag = GraphRAGEngine(storage_path=str(data_dir / "graphrag"))
        self.memory = NetworkedMemory(storage_path=str(data_dir / "memory"))
        self.workflows = WorkflowEngine(workflows_dir=str(ABM_ROOT / "core" / "workflows" / "definitions"))
        self.decision_governor = allow_external_calls

        self.creative = CreativeModule(self.llm.complete)
        self.analyzer = CustomAnalyzerAgent(self.llm.complete)
        self.sentiment = SentimentService()

        self.network = AgentNetwork()
        self.network.spawn_default_fleet(knowledge_source=self.knowledge_tank)
        self.network.register("creative-1", ModuleExecutor(
            "creative", "creative", ["brainstorm", "ideate"], self.creative.process))
        self.network.register("analyzer-1", ModuleExecutor(
            "analyzer", "analysis", ["trend", "risk", "opportunity", "pattern"], self.analyzer.run))
        self.network.register("sentiment-1", ModuleExecutor(
            "sentiment", "analysis", ["sentiment", "crypto"], self.sentiment.analyze_goal))

        self.telegram = TelegramBotService(
            self.config.telegram,
            process_goal=self._process_goal_for_telegram,
            get_status=self.health,
            get_agents=self.agents,
            get_memory=self.memory_state,
        )
        self.subscribe(self.telegram.on_orchestrator_event)

        self._register_services()

    # -- service registry ---------------------------------------------------

    def _register_services(self) -> None:
        for name, service in {
            "orchestrator": self,
            "llm": self.llm,
            "brain": self.brain,
            "knowledge_tank": self.knowledge_tank,
            "graphrag": self.graphrag,
            "memory": self.memory,
            "workflows": self.workflows,
            "agent_network": self.network,
            "decision_governor": self.decision_governor,
            "creative": self.creative,
            "analyzer": self.analyzer,
            "sentiment": self.sentiment,
            "telegram": self.telegram,
        }.items():
            self.registry.register(name, service)

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Start the long-running services (Telegram transport). Idempotent."""
        if self.running:
            return
        self.running = True
        await self.telegram.start()
        logger.info("Orchestrator online: %d agents, %d services",
                    len(self.network.profiles), len(self.registry.list_services()))

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        await self.telegram.stop()

    # -- events -------------------------------------------------------------

    def subscribe(self, listener: EventListener) -> None:
        self._listeners.append(listener)

    async def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        event = {"type": event_type, "data": data, "time": _timestamp()}
        for listener in self._listeners:
            try:
                await listener(event)
            except Exception:
                logger.exception("Event listener failed for %s", event_type)

    # -- task execution -----------------------------------------------------

    def record_policy_event(self, context: str, result: str) -> Dict[str, str]:
        entry = {
            "time": _timestamp(),
            "event": "policy_check",
            "context": context,
            "result": result,
            "agent": "task_dispatcher",
            "policy": "External Task Execution",
            "detail": f"Task execution {result}",
        }
        self.governance_log.append(entry)
        return entry

    async def _process_goal_for_telegram(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return await self.process_goal(description, 5, context)

    async def process_goal(
        self, description: str, priority: int = 5, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run a goal through the agent network, persist it and update shared state."""
        context = context or {}
        source = context.get("source", "api")
        task_id = f"task-{uuid.uuid4().hex}"
        entry: Dict[str, Any] = {
            "id": task_id,
            "description": description,
            "priority": priority,
            "status": "running",
            "progress": 0,
            "agent": None,
            "created": _timestamp(),
            "result": None,
            "execution_mode": None,
        }
        self.state_store.save_task(entry)

        agent_id = self.network.select_agent(description)
        if agent_id != "research-1" and not self.decision_governor("task_execution"):
            self.record_policy_event("task_execution", "blocked")
            entry.update(
                status="failed",
                agent=agent_id,
                result={"error": "External task execution is blocked by policy"},
                execution_mode="blocked",
            )
        else:
            try:
                result = await self.network.dispatch(agent_id, {
                    "goal": description,
                    "input": description,
                    "query": description,
                    "context": context,
                })
                status = "completed" if result.get("success") else "failed"
                entry.update(
                    status=status,
                    progress=100 if status == "completed" else 0,
                    agent=agent_id,
                    result=result,
                    execution_mode=result.get("execution_mode", "error"),
                )
            except Exception as exc:
                logger.exception("Task execution failed")
                entry.update(status="failed", agent=agent_id, result={"error": str(exc)},
                             execution_mode="error")

        self.state_store.save_task(entry)
        await self._record_outcome(entry, source)
        await self.emit("task", {**entry, "source": source})
        return entry

    async def _record_outcome(self, entry: Dict[str, Any], source: str) -> None:
        """Write the task into brain, memory, knowledge tank and graph, then emit events."""
        description = entry["description"]
        result = entry.get("result") or {}
        outcome = str(result.get("result", result.get("error", "")))
        self.brain.remember(entry["id"], f"{description} -> {entry['status']}")
        self.memory.remember(f"{description}\n{outcome}", {"task_id": entry["id"], "status": entry["status"]})
        if entry["status"] == "completed" and entry["execution_mode"] == "live":
            self.knowledge_tank.ingest_bulk([{
                "category": "task_result",
                "content": outcome,
                "tags": [entry["agent"]],
                "source": entry["id"],
                "metadata": {"task_id": entry["id"], "description": description},
            }])
        task_node = self.graphrag.add_node(
            description[:48], description, "task",
            metadata={"task_id": entry["id"], "status": entry["status"]},
        )
        self.graphrag.add_edge(self._agent_node(entry["agent"]), task_node, "executed")
        await self.emit("memory", {"stats": self.memory.stats(), "source": source})
        await self.emit("graph", {"nodes": len(self.graphrag.nodes),
                                  "edges": len(self.graphrag.edges), "source": source})

    def _agent_node(self, agent_id: str) -> str:
        for node in self.graphrag.nodes.values():
            if node.node_type == "agent" and node.label == agent_id:
                return node.id
        return self.graphrag.add_node(agent_id, f"Agent {agent_id}", "agent", auto_link=False)

    # -- live state ---------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        return {
            "status": "online" if self.running else "booting",
            "uptime": round(time.time() - self.started_at, 1),
            "timestamp": _timestamp(),
            "modules": {
                "brain": True,
                "knowledge_tank": True,
                "graphrag": True,
                "memory": True,
                "agent_network": True,
                "workflows": True,
                "llm": self.llm.describe(),
                "telegram": {"transport": "connected" if self.telegram.enabled else "webhook-only"},
            },
            "services": self.registry.list_services(),
            "agents": len(self.network.profiles),
        }

    def agents(self) -> Dict[str, Any]:
        agents = []
        for profile in self.network.profiles.values():
            agents.append({
                "id": profile.agent_id,
                "name": profile.name,
                "type": {"execution": "worker", "research": "specialist",
                         "analysis": "coordinator", "oversight": "monitor"}.get(profile.role, profile.role),
                "status": profile.status,
                "health": None,
                "cpu": None,
                "memory": None,
                "capabilities": profile.capabilities,
                "tasks_completed": profile.total_tasks,
                "uptime": None,
                "current_tasks": 1 if profile.status == "busy" else 0,
                "source": "agent_network",
            })
        return {"agents": agents, "count": len(agents)}

    def graph_state(self, limit: int = 200) -> Dict[str, Any]:
        nodes = list(self.graphrag.nodes.values())[-limit:]
        ids = {n.id for n in nodes}
        stats = self.graphrag.get_stats()
        return {
            "stats": {**stats, "node_types": sorted(stats["node_types"]),
                      "edge_types": sorted(stats["edge_types"])},
            "nodes": [{"id": n.id, "label": n.label, "type": n.node_type, "metadata": n.metadata}
                      for n in nodes],
            "edges": [{"from": e.source, "to": e.target, "type": e.edge_type, "weight": e.weight}
                      for e in self.graphrag.edges if e.source in ids and e.target in ids],
            "count": len(nodes),
        }

    def memory_state(self) -> Dict[str, Any]:
        return {
            "networked": self.memory.stats(),
            "knowledge_tank": self.knowledge_tank.get_stats(),
            "brain": {"memory_nodes": len(self.brain.memory_graph), "decisions": self.brain.decisions},
        }


_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Return the process-wide orchestrator, building it on first use."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def set_orchestrator(orchestrator: Orchestrator) -> None:
    global _orchestrator
    _orchestrator = orchestrator


if __name__ == "__main__":
    from main import main

    main()
