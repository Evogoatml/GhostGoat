#!/usr/bin/env python3
"""
GhostGoat API Server — exposes real modules over HTTP.
Dashboard connects here. Falls back to simulation when this isn't running.

Start: python -m api.server
"""

import asyncio
import os
import sys
import time
import json
import logging
import psutil
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostgoat.api")

# ── Safe imports of real modules (graceful degradation) ──────────────

def _try_import(label, fn):
    try:
        result = fn()
        logger.info(f"  [+] {label}")
        return result
    except Exception as e:
        logger.warning(f"  [-] {label}: {e}")
        return None

logger.info("Loading GhostGoat modules...")

service_registry = _try_import("ServiceRegistry",
    lambda: __import__("core.service_registry", fromlist=["registry"]).registry)

decision_governor = _try_import("DecisionGovernor",
    lambda: __import__("core.governance.decision_governor", fromlist=["allow_external_calls"]))

task_handler_mod = _try_import("TaskHandler",
    lambda: __import__("core.task_handler", fromlist=["handle_task", "handle_task_async"]))

efficiency_engine = _try_import("EfficiencyEngine",
    lambda: __import__("core.agents.agent_core.efficiency_engine", fromlist=["analyze_efficiency"]))

knowledge_tank_mod = _try_import("KnowledgeTank",
    lambda: __import__("core.reasoning.brain.knowledge.knowledge_tank", fromlist=["KnowledgeTank"]))

# Try the orchestrator (heavy — may fail if deps missing)
orchestrator_instance = None
def _load_orchestrator():
    global orchestrator_instance
    try:
        # FIXME: orchestrator import disabled - module path unknown
        orchestrator_instance = LLMOrchestrator(
            llm_provider=os.getenv("LLM_PROVIDER", "mock"),
            base_path=ROOT
        )
        logger.info("  [+] LLMOrchestrator (provider=%s)", os.getenv("LLM_PROVIDER", "mock"))
    except Exception as e:
        logger.warning(f"  [-] LLMOrchestrator: {e}")

_load_orchestrator()

# Nanoagent system
nanoagent_spawner = _try_import("NanoagentSpawner",
    lambda: __import__("agents.nanoagent", fromlist=["spawner"]).spawner)

# Tool registry
tool_registry = _try_import("ToolRegistry",
    lambda: __import__("tools.registry", fromlist=["registry"]).registry)

logger.info("Module loading complete.")

# ── Tracking state ───────────────────────────────────────────────────

_start_time = time.time()
_task_log: List[Dict] = []
_message_log: List[Dict] = []
_governance_log: List[Dict] = []

# ── FastAPI app ──────────────────────────────────────────────────────

app = FastAPI(title="GhostGoat API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request models ───────────────────────────────────────────────────

class TaskRequest(BaseModel):
    description: str
    priority: int = 5
    context: Optional[Dict[str, Any]] = None

class MessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    content: str
    type: str = "task_assign"

# ── Health & system endpoints ────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "uptime": round(time.time() - _start_time, 1),
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "service_registry": service_registry is not None,
            "decision_governor": decision_governor is not None,
            "task_handler": task_handler_mod is not None,
            "efficiency_engine": efficiency_engine is not None,
            "knowledge_tank": knowledge_tank_mod is not None,
            "orchestrator": orchestrator_instance is not None,
        }
    }

@app.get("/api/system/metrics")
def system_metrics():
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "memory_used_mb": round(mem.used / 1024 / 1024),
        "memory_total_mb": round(mem.total / 1024 / 1024),
        "disk_percent": disk.percent,
        "process_count": len(psutil.pids()),
        "timestamp": datetime.now().isoformat(),
    }

# ── Agent endpoints (real registry) ─────────────────────────────────

@app.get("/api/agents")
def list_agents():
    agents = []

    # From service registry
    if service_registry:
        for name, is_live in service_registry.list_services().items():
            agents.append({
                "id": f"svc-{name}",
                "name": name,
                "type": "service",
                "status": "active" if is_live else "pending",
                "source": "service_registry",
            })

    # From orchestrator agent profiles
    if orchestrator_instance and hasattr(orchestrator_instance, "agent_profiles"):
        for name, profile in orchestrator_instance.agent_profiles.items():
            agents.append({
                "id": f"orch-{name}",
                "name": profile.name,
                "type": "orchestrator_agent",
                "status": profile.status,
                "host": profile.host,
                "port": profile.port,
                "capabilities": [c.value for c in profile.capabilities],
                "current_tasks": profile.current_tasks,
                "max_tasks": profile.max_concurrent_tasks,
                "source": "orchestrator",
            })

    # Built-in modules that are loaded
    builtins = [
        ("Brain Core", "core.reasoning.brain.core", "coordinator"),
        ("Decision Governor", "core.governance.decision_governor", "governance"),
        ("Task Handler", "core.task_handler", "worker"),
        ("Efficiency Engine", "core.agents.agent_core.efficiency_engine", "monitor"),
        ("Knowledge Tank", "core.reasoning.brain.knowledge.knowledge_tank", "specialist"),
    ]
    for name, module, atype in builtins:
        loaded = module.split(".")[-1] in [
            "decision_governor" if decision_governor else "",
            "task_handler" if task_handler_mod else "",
            "efficiency_engine" if efficiency_engine else "",
            "knowledge_tank" if knowledge_tank_mod else "",
        ] or (name == "Brain Core" and orchestrator_instance is not None)

        agents.append({
            "id": f"mod-{module}",
            "name": name,
            "type": atype,
            "status": "active" if loaded else "offline",
            "module": module,
            "source": "builtin",
        })

    return {"agents": agents, "count": len(agents)}

# ── Task endpoints (real task handler + orchestrator) ────────────────

@app.get("/api/tasks")
def list_tasks():
    tasks = list(_task_log)

    # Also pull from orchestrator's internal task list
    if orchestrator_instance and hasattr(orchestrator_instance, "tasks"):
        for tid, task in orchestrator_instance.tasks.items():
            tasks.append({
                "id": tid,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "agent": task.assigned_agent,
                "created": task.created_at,
                "source": "orchestrator",
            })

    return {"tasks": tasks, "count": len(tasks)}

@app.post("/api/tasks")
async def create_task(req: TaskRequest):
    task_id = f"task-{int(time.time()*1000)}"
    entry = {
        "id": task_id,
        "description": req.description,
        "priority": req.priority,
        "status": "running",
        "agent": None,
        "created": datetime.now().isoformat(),
        "result": None,
    }
    _task_log.append(entry)

    # Try orchestrator first (full decompose + multi-agent)
    if orchestrator_instance:
        try:
            result = await orchestrator_instance.orchestrate(req.description, req.context)
            entry["status"] = "completed"
            entry["result"] = result
            entry["agent"] = "LLMOrchestrator"
            return {"task": entry}
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            entry["status"] = "failed"
            entry["result"] = {"error": str(e)}

    # Fallback to simple task handler
    if task_handler_mod:
        try:
            result = await task_handler_mod.handle_task_async(req.description, req.context)
            entry["status"] = "completed"
            entry["result"] = result
            entry["agent"] = "TaskHandler"
            return {"task": entry}
        except Exception as e:
            entry["status"] = "failed"
            entry["result"] = {"error": str(e)}

    if entry["status"] == "running":
        entry["status"] = "failed"
        entry["result"] = {"error": "No task handler available"}

    return {"task": entry}

# ── Governance endpoints (real decision governor) ────────────────────

@app.get("/api/governance/policies")
def get_policies():
    policies = []

    if decision_governor:
        # The real governor uses env-based policy. Expose it.
        ext_allowed = decision_governor.allow_external_calls("diagnostic")
        policies.append({
            "id": "pol-ext",
            "name": "External API Access",
            "scope": "diagnostic",
            "status": "enforced",
            "allowed": ext_allowed,
            "env_var": "ADAP_ALLOW_EXTERNAL",
            "env_value": os.getenv("ADAP_ALLOW_EXTERNAL", "1"),
        })
        # Log it
        _governance_log.append({
            "time": datetime.now().isoformat(),
            "event": "policy_check",
            "policy": "External API Access",
            "result": "allowed" if ext_allowed else "blocked",
        })

    return {"policies": policies, "audit_log": _governance_log[-50:]}

@app.post("/api/governance/check")
async def check_policy(context: str = "diagnostic"):
    if not decision_governor:
        raise HTTPException(503, "Decision governor not loaded")

    allowed = decision_governor.allow_external_calls(context)
    entry = {
        "time": datetime.now().isoformat(),
        "event": "policy_check",
        "context": context,
        "result": "allowed" if allowed else "blocked",
    }
    _governance_log.append(entry)
    return entry

# ── Knowledge endpoints ──────────────────────────────────────────────

@app.get("/api/knowledge/search")
def search_knowledge(q: str, limit: int = 10):
    if orchestrator_instance and hasattr(orchestrator_instance, "knowledge_tank") and orchestrator_instance.knowledge_tank:
        try:
            results = orchestrator_instance.knowledge_tank.search(q, limit=limit)
            return {"query": q, "results": results, "count": len(results)}
        except Exception as e:
            return {"query": q, "results": [], "error": str(e)}
    return {"results": [], "error": "Orchestrator not available"}

# ── Messages (inter-agent comms log) ────────────────────────────────

@app.get("/api/messages")
def list_messages():
    return {"messages": _message_log[-100:], "count": len(_message_log)}

@app.post("/api/messages")
def send_message(req: MessageRequest):
    entry = {
        "id": f"msg-{int(time.time()*1000)}",
        "from": req.from_agent,
        "to": req.to_agent,
        "content": req.content,
        "type": req.type,
        "time": datetime.now().isoformat(),
        "status": "delivered",
    }
    _message_log.append(entry)
    return entry

# ── Service registry endpoints ───────────────────────────────────────

@app.get("/api/services")
def list_services():
    if not service_registry:
        return {"services": {}, "error": "Registry not loaded"}
    return {"services": service_registry.list_services()}

# ── Nanoagent endpoints ──────────────────────────────────────────────

class NanoagentRequest(BaseModel):
    task_type: str  # file_scan, port_scan, hash_compute, http_check, system_info
    task: str = ""
    context: Optional[Dict[str, Any]] = None

@app.get("/api/nanoagents")
def list_nanoagents():
    if not nanoagent_spawner:
        return {"active": [], "history": [], "error": "Nanoagent system not loaded"}
    return {
        "active": nanoagent_spawner.list_active(),
        "history": nanoagent_spawner.get_history(20),
    }

@app.post("/api/nanoagents/execute")
def execute_nanoagent(req: NanoagentRequest):
    if not nanoagent_spawner:
        raise HTTPException(503, "Nanoagent system not loaded")
    result = nanoagent_spawner.execute(req.task_type, req.task, req.context)
    return result

# ── Poster generation workflow ───────────────────────────────────────

class PosterRequest(BaseModel):
    platform: str = "Instagram"        # Instagram | LinkedIn | Twitter | YouTube
    tone: str = "professional"         # professional | casual | energetic | fun | witty
    input_text: str
    poster_prompt: str = ""
    brand_guidelines: Optional[str] = None
    logo_base64: Optional[str] = None  # base64-encoded logo image
    logo_position: str = "top-right"

@app.post("/api/poster/generate")
async def generate_poster(req: PosterRequest):
    try:
        import importlib.util, os as _os
        _mod_path = _os.path.join(
            ROOT,
            "core", "agents", "frameworks", "agent_frameworks",
            "marketing", "Agentic-Ads", "backend", "rag", "poster_generation.py"
        )
        _spec = importlib.util.spec_from_file_location("poster_generation", _mod_path)
        if _spec is None or not _os.path.exists(_mod_path):
            raise ImportError(f"Cannot locate poster_generation.py at {_mod_path}")
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        PosterGenerationContext = _mod.PosterGenerationContext
        PosterGenerationAgent = _mod.PosterGenerationAgent
    except Exception as e:
        raise HTTPException(503, f"Poster generation module not available: {e}")

    import base64 as _b64
    logo_bytes = _b64.b64decode(req.logo_base64) if req.logo_base64 else None

    ctx = PosterGenerationContext(
        platform=req.platform,
        tone=req.tone,
        brand_guidelines=req.brand_guidelines,
        input_text=req.input_text,
        poster_prompt=req.poster_prompt or req.input_text,
        logo_data=logo_bytes,
        logo_position=req.logo_position,
    )
    agent = PosterGenerationAgent(ctx)
    result = await agent.generate_poster({
        "platform": req.platform,
        "tone": req.tone,
        "input_text": req.input_text,
        "poster_prompt": req.poster_prompt or req.input_text,
    })
    return result

@app.get("/api/posters/download/{filename}")
async def download_poster(filename: str):
    import tempfile
    from pathlib import Path
    from fastapi.responses import FileResponse
    temp_dir = Path(tempfile.gettempdir()) / "agentic_ads_posters"
    file_path = temp_dir / filename
    if not file_path.exists():
        raise HTTPException(404, "Poster not found")
    return FileResponse(str(file_path), media_type="image/png", filename=filename)

# ── Tool endpoints ───────────────────────────────────────────────────

@app.get("/api/tools")
def list_tools():
    if not tool_registry:
        return {"tools": [], "error": "Tool registry not loaded"}
    return {"tools": tool_registry.list_tools()}

@app.post("/api/tools/execute")
def execute_tool(name: str, params: Optional[Dict[str, Any]] = None):
    if not tool_registry:
        raise HTTPException(503, "Tool registry not loaded")
    result = tool_registry.execute_tool(name, **(params or {}))
    return {"tool": name, "success": result.success, "output": result.output, "error": result.error}

# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8420, log_level="info")
