#!/usr/bin/env python3
"""Canonical GhostGoat API for the supported root runtime."""

import contextlib
import importlib
import itertools
import logging
import math
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import psutil
except ImportError:
    psutil = None

ROOT = Path(__file__).resolve().parents[2]
ABM_ROOT = ROOT / "agent_byte-master"
for path in (str(ROOT), str(ABM_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from config.api.state_store import RuntimeState
from config.unified_config import TelegramConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostgoat.api")


def _try_import(label: str, fn):
    try:
        result = fn()
        logger.info("Loaded %s", label)
        return result
    except Exception as exc:
        logger.warning("Unavailable %s: %s", label, exc)
        return None


service_registry = _try_import(
    "service registry",
    lambda: importlib.import_module("core.service_registry").registry,
)
decision_governor = _try_import(
    "decision governor",
    lambda: importlib.import_module(
        "core.governance.decision_governor"
    ).allow_external_calls,
)
knowledge_tank = _try_import(
    "knowledge store",
    lambda: importlib.import_module("brain.knowledge.knowledge_tank").KnowledgeTank(
        storage_path=os.getenv(
            "GHOSTGOAT_KNOWLEDGE_PATH", str(ROOT / ".backend" / "knowledge_tank")
        )
    ),
)
orchestrator_instance = None
try:
    agent_network_module = importlib.import_module("agents.agent_network")
    orchestrator_instance = agent_network_module.AgentNetwork()
    orchestrator_instance.spawn_default_fleet(knowledge_source=knowledge_tank)
    logger.info("Loaded task dispatcher and default agent fleet")
except Exception as exc:
    logger.warning("Unavailable task dispatcher: %s", exc)

state_store = RuntimeState()
_start_time = time.time()
_governance_log: list[dict[str, Any]] = []

telegram_service = None


def _build_telegram_service():
    """Create the Telegram service only when TELEGRAM_BOT_TOKEN is configured."""
    config = TelegramConfig.from_env()
    if not config.enabled:
        return None
    try:
        module = importlib.import_module("services.telegram_bot")
    except Exception as exc:
        logger.warning("Unavailable telegram service: %s", exc)
        return None
    return module.TelegramBotService(
        config,
        process_goal=_process_goal_for_telegram,
        get_status=lambda: health(),
        get_agents=lambda: list_agents(),
        get_memory=lambda: memory_stats(),
    )


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    global telegram_service
    if telegram_service is None:
        telegram_service = _build_telegram_service()
    if telegram_service is not None:
        await telegram_service.start()
    try:
        yield
    finally:
        if telegram_service is not None:
            await telegram_service.stop()


app = FastAPI(title="GhostGoat API", version="2.0.0", lifespan=lifespan)
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "GHOSTGOAT_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    description: str = Field(min_length=1, max_length=10_000)
    priority: int = Field(default=5, ge=1, le=10)
    context: Optional[dict[str, Any]] = None


class MessageRequest(BaseModel):
    from_agent: str = Field(min_length=1, max_length=200)
    to_agent: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)
    type: str = Field(default="task_assign", max_length=100)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_orchestrator():
    """Load the supported in-process task dispatcher and default fleet."""
    global orchestrator_instance
    if orchestrator_instance is None:
        try:
            module = importlib.import_module("agents.agent_network")
            orchestrator_instance = module.AgentNetwork()
            orchestrator_instance.spawn_default_fleet(knowledge_source=knowledge_tank)
        except Exception:
            logger.exception("Could not initialize task dispatcher")
            return None
    return orchestrator_instance


@app.get("/api/health")
def health():
    return {
        "status": "online",
        "uptime": round(time.time() - _start_time, 1),
        "timestamp": _timestamp(),
        "modules": {
            "service_registry": service_registry is not None,
            "decision_governor": decision_governor is not None,
            "knowledge_tank": knowledge_tank is not None,
            "orchestrator": orchestrator_instance is not None,
        },
    }


@app.get("/api/system/metrics")
def system_metrics():
    if psutil is None:
        raise HTTPException(status_code=503, detail="psutil is unavailable")
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(ROOT))
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": memory.percent,
        "memory_used_mb": round(memory.used / 1024 / 1024),
        "memory_total_mb": round(memory.total / 1024 / 1024),
        "disk_percent": disk.percent,
        "process_count": len(psutil.pids()),
        "timestamp": _timestamp(),
    }


@app.get("/api/agents")
def list_agents():
    network = _load_orchestrator()
    agents = []
    if network:
        for profile in network.profiles.values():
            agent_type = {
                "execution": "worker",
                "research": "specialist",
                "analysis": "coordinator",
                "oversight": "monitor",
            }.get(profile.role, profile.role)
            agents.append({
                "id": profile.agent_id,
                "name": profile.name,
                "type": agent_type,
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


@app.get("/api/tasks")
def list_tasks():
    tasks = state_store.list_tasks()
    return {"tasks": tasks, "count": len(tasks)}


@app.post("/api/tasks")
async def create_task(req: TaskRequest):
    entry = await process_goal(req.description, req.priority, req.context)
    if telegram_service is not None and (req.context or {}).get("source") != "telegram":
        await telegram_service.notify(telegram_service.format_task(entry))
    return {"task": entry}


async def _process_goal_for_telegram(description: str, context: dict[str, Any]) -> dict[str, Any]:
    return await process_goal(description, 5, context)


async def process_goal(
    description: str, priority: int = 5, context: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Run a goal through the orchestrator and persist the task."""
    network = _load_orchestrator()
    task_id = f"task-{uuid.uuid4().hex}"
    entry: dict[str, Any] = {
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
    state_store.save_task(entry)

    if network is None:
        entry.update(status="failed", result={"error": "No task dispatcher available"})
        state_store.save_task(entry)
        return entry

    agent_id = network.select_agent(description)
    if agent_id != "research-1" and (
        decision_governor is None or not decision_governor("task_execution")
    ):
        _record_policy_event("task_execution", "blocked")
        reason = (
            "Decision governor is unavailable"
            if decision_governor is None
            else "External task execution is blocked by policy"
        )
        entry.update(
            status="failed",
            agent=agent_id,
            result={"error": reason},
            execution_mode="blocked",
        )
        state_store.save_task(entry)
        return entry

    try:
        result = await network.dispatch(
            agent_id,
            {
                "goal": description,
                "input": description,
                "query": description,
                "context": context or {},
            },
        )
        mode = result.get("execution_mode", "mock")
        status = (
            "mocked" if mode == "mock"
            else "completed" if result.get("success")
            else "failed"
        )
        entry.update(
            status=status,
            progress=100 if status == "completed" else 0,
            agent=agent_id,
            result=result,
            execution_mode=mode,
        )
        if (
            status == "completed"
            and mode == "live"
            and agent_id == "analyst-1"
            and knowledge_tank is not None
        ):
            knowledge_tank.ingest_bulk([{
                "category": "task_result",
                "content": str(result.get("result", "")),
                "tags": [agent_id],
                "source": task_id,
                "metadata": {"task_id": task_id, "description": description},
            }])
    except Exception as exc:
        logger.exception("Task execution failed")
        entry.update(
            status="failed",
            agent=agent_id,
            result={"error": str(exc)},
            execution_mode="error",
        )

    state_store.save_task(entry)
    return entry


@app.get("/api/governance/policies")
def get_policies():
    policies = []
    if decision_governor:
        allowed = decision_governor("task_execution")
        policies.append({
            "id": "pol-external",
            "name": "External Task Execution",
            "scope": "task_execution",
            "action": "allow_external_calls",
            "status": "enforced",
            "allowed": allowed,
            "violations": sum(e["result"] == "blocked" for e in _governance_log),
        })
    return {"policies": policies, "audit_log": list(reversed(_governance_log[-50:]))}


def _record_policy_event(context: str, result: str) -> dict[str, str]:
    entry = {
        "time": _timestamp(),
        "event": "policy_check",
        "context": context,
        "result": result,
        "agent": "task_dispatcher",
        "policy": "External Task Execution",
        "detail": f"Task execution {result}",
    }
    _governance_log.append(entry)
    return entry


@app.post("/api/governance/check")
def check_policy(context: str = "task_execution"):
    if not decision_governor:
        raise HTTPException(status_code=503, detail="Decision governor unavailable")
    allowed = decision_governor(context)
    return _record_policy_event(context, "allowed" if allowed else "blocked")


@app.get("/api/knowledge/search")
def search_knowledge(q: str, limit: int = 10):
    if knowledge_tank is None:
        raise HTTPException(status_code=503, detail="Knowledge store unavailable")
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    results = knowledge_tank.search(q, limit=limit)
    return {"query": q, "results": results, "count": len(results)}


@app.get("/api/knowledge/graph")
def knowledge_graph():
    if knowledge_tank is None:
        raise HTTPException(status_code=503, detail="Knowledge store unavailable")
    entries = list(itertools.islice(reversed(knowledge_tank.entries.values()), 100))
    count = len(entries)
    nodes = []
    for index, entry in enumerate(entries):
        angle = 2 * math.pi * index / max(count, 1)
        nodes.append({
            "id": entry.id,
            "label": entry.content[:48] or entry.category,
            "group": entry.category,
            "x": 450 + 350 * math.cos(angle),
            "y": 250 + 190 * math.sin(angle),
            "tags": entry.tags,
        })
    edges = []
    for index, first in enumerate(entries):
        if len(edges) >= 500:
            break
        for second in entries[index + 1:]:
            shared_tags = set(first.tags) & set(second.tags)
            if shared_tags or first.category == second.category:
                edges.append({"from": first.id, "to": second.id})
                if len(edges) >= 500:
                    break
    return {"nodes": nodes, "edges": edges, "count": len(nodes)}


@app.get("/api/memory/search")
def search_memory(q: str = "", limit: int = 50):
    if knowledge_tank is None:
        raise HTTPException(status_code=503, detail="Memory store unavailable")
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    entries = knowledge_tank.search(q, limit=limit) if q else [
        {
            "id": entry.id,
            "category": entry.category,
            "content": entry.content,
            "tags": entry.tags,
            "source": entry.source,
            "confidence": entry.confidence,
            "usage": entry.usage_count,
        }
        for entry in itertools.islice(reversed(knowledge_tank.entries.values()), limit)
    ]
    return {"entries": entries, "count": len(entries), "source": "knowledge_tank"}


@app.get("/api/memory/stats")
def memory_stats():
    if knowledge_tank is None:
        raise HTTPException(status_code=503, detail="Memory store unavailable")
    return knowledge_tank.get_stats()


@app.get("/api/messages")
def list_messages():
    messages = state_store.list_messages()
    return {"messages": messages, "count": len(messages), "delivery": "log_only"}


@app.post("/api/messages")
def send_message(req: MessageRequest):
    message = {
        "id": f"msg-{uuid.uuid4().hex}",
        "from": req.from_agent,
        "to": req.to_agent,
        "content": req.content,
        "type": req.type,
        "time": _timestamp(),
        "status": "logged",
        "delivery": "log_only",
    }
    state_store.save_message(message)
    return message


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    if telegram_service is None:
        raise HTTPException(status_code=503, detail="Telegram bot is not configured")
    if not telegram_service.verify_secret(x_telegram_bot_api_secret_token):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    try:
        update = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Invalid update")
    await telegram_service.handle_update(update)
    return {"ok": True}


@app.get("/api/services")
def list_services():
    if service_registry is None:
        return {"services": {}, "error": "Service registry unavailable"}
    return {"services": service_registry.list_services()}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("GHOSTGOAT_HOST", "127.0.0.1"),
        port=8420,
        log_level="info",
    )
