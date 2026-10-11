#!/usr/bin/env python3
"""Canonical GhostGoat REST front end; every route delegates to the shared orchestrator."""

import contextlib
import itertools
import logging
import math
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import psutil

ROOT = Path(__file__).resolve().parents[2]
ABM_ROOT = ROOT / "agent_byte-master"
for path in (str(ROOT), str(ABM_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.unified_config import get_config
from run_cognitive_system import get_orchestrator

logger = logging.getLogger("ghostgoat.api")


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    orchestrator = get_orchestrator()
    await orchestrator.start()
    try:
        yield
    finally:
        await orchestrator.stop()


app = FastAPI(title="GhostGoat API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_config().runtime.cors_origins,
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


@app.get("/api/health")
def health():
    return get_orchestrator().health()


@app.get("/api/system/metrics")
def system_metrics():
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
    return get_orchestrator().agents()


@app.get("/api/graph")
def graph():
    return get_orchestrator().graph_state()


@app.get("/api/memory")
def memory():
    return get_orchestrator().memory_state()


@app.get("/api/tasks")
def list_tasks():
    tasks = get_orchestrator().state_store.list_tasks()
    return {"tasks": tasks, "count": len(tasks)}


@app.post("/api/tasks")
async def create_task(req: TaskRequest):
    entry = await get_orchestrator().process_goal(req.description, req.priority, req.context)
    return {"task": entry}


@app.get("/api/governance/policies")
def get_policies():
    orchestrator = get_orchestrator()
    log = orchestrator.governance_log
    policy = {
        "id": "pol-external",
        "name": "External Task Execution",
        "scope": "task_execution",
        "action": "allow_external_calls",
        "status": "enforced",
        "allowed": orchestrator.decision_governor("task_execution"),
        "violations": sum(e["result"] == "blocked" for e in log),
    }
    return {"policies": [policy], "audit_log": list(reversed(log[-50:]))}


@app.post("/api/governance/check")
def check_policy(context: str = "task_execution"):
    orchestrator = get_orchestrator()
    allowed = orchestrator.decision_governor(context)
    return orchestrator.record_policy_event(context, "allowed" if allowed else "blocked")


@app.get("/api/knowledge/search")
def search_knowledge(q: str, limit: int = 10):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    results = get_orchestrator().knowledge_tank.search(q, limit=limit)
    return {"query": q, "results": results, "count": len(results)}


@app.get("/api/knowledge/graph")
def knowledge_graph():
    knowledge_tank = get_orchestrator().knowledge_tank
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
    knowledge_tank = get_orchestrator().knowledge_tank
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
    return get_orchestrator().knowledge_tank.get_stats()


@app.get("/api/messages")
def list_messages():
    messages = get_orchestrator().state_store.list_messages()
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
    get_orchestrator().state_store.save_message(message)
    return message


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    telegram = get_orchestrator().telegram
    if not telegram.verify_secret(x_telegram_bot_api_secret_token):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    try:
        update = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Invalid update")
    reply = await telegram.handle_update(update)
    return {"ok": True, "reply": reply}


@app.get("/api/services")
def list_services():
    return {"services": get_orchestrator().registry.list_services()}


if __name__ == "__main__":
    from main import main

    main()
