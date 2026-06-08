#!/usr/bin/env python3
"""GhostGoat Cognitive API — FastAPI with full Tool Intelligence layer."""
import asyncio, json, os, sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
ABM_ROOT = str(ROOT / "agent_byte-master")
if ABM_ROOT not in sys.path:
    sys.path.insert(0, ABM_ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from run_cognitive_system import bootstrap
from functools import partial

app = FastAPI(title="GhostGoat Cognitive API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_system: Optional[Dict[str, Any]] = None


def _ensure_system():
    """Lazy bootstrap on first request."""
    global _system
    if _system is None:
        _system = bootstrap()
        # Also init tools
        from toolkit import ToolRegistry, ToolSelector, ToolExecutor, ToolMemory
        from toolkit.adaptive_executor import AdaptiveExecutor
        _system["tools"] = ToolRegistry()
        _system["tool_selector"] = ToolSelector(_system["tools"])
        _system["tool_executor"] = ToolExecutor(_system["tools"])
        _system["adaptive_executor"] = AdaptiveExecutor(_system["tools"], max_parallel=4)
        _system["tool_memory"] = ToolMemory()
    return _system


class GoalRequest(BaseModel):
    goal: str
    context: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    workflow_name: str
    payload: Dict[str, Any]


class ToolSelectRequest(BaseModel):
    task: str
    fast_mode: bool = False


class ToolRunRequest(BaseModel):
    selections: List[Dict[str, Any]]
    context: Optional[Dict[str, Any]] = None


@app.on_event("startup")
async def startup():
    _ensure_system()


@app.get("/health")
def health():
    return {"status": "healthy", "system": "cognitive", "version": "3.0.0"}


# ═══════════════════════════════════════════════════════════
# COGNITIVE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.post("/v2/cognitive/process")
async def process_goal(req: GoalRequest):
    s = _ensure_system()
    engine = s["engine"]
    network = s["network"]
    agents = {aid: partial(network.dispatch, aid) for aid in network.executors.keys()}
    return await engine.process(req.goal, context=req.context, agents=agents)


@app.post("/v2/cognitive/workflow")
async def run_workflow(req: WorkflowRequest):
    s = _ensure_system()
    return await s["workflows"].run(req.workflow_name, req.payload, agent_network=s["network"])


@app.get("/v2/cognitive/status")
def status():
    s = _ensure_system()
    return {"brain": s["brain"].get_state(), "network": s["network"].get_fleet_status(),
            "workflows": s["workflows"].list_workflows(), "memory": s["memory"].stats(),
            "graphrag": s["graphrag"].get_stats(), "knowledge_tank": s["knowledge_tank"].get_stats()}


@app.get("/v2/cognitive/agents")
def list_agents():
    return _ensure_system()["network"].get_fleet_status()


@app.get("/v2/cognitive/workflows")
def list_workflows():
    return _ensure_system()["workflows"].list_workflows()


@app.get("/v2/cognitive/memory/search")
def memory_search(q: str, top_k: int = 5):
    return {"results": _ensure_system()["memory"].recall(q, top_k)}


@app.get("/v2/cognitive/graph/search")
def graph_search(q: str, top_k: int = 5):
    s = _ensure_system()
    qvec = s["graphrag"]._deterministic_embed(q)
    return {"results": s["graphrag"].search(qvec, top_k=top_k)}


@app.get("/v2/cognitive/knowledge/search")
def knowledge_search(q: str, limit: int = 10):
    return {"results": _ensure_system()["knowledge_tank"].search(q, limit=limit)}


# ═══════════════════════════════════════════════════════════
# TOOL INTELLIGENCE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/v2/tools/list")
def list_tools(category: Optional[str] = None):
    s = _ensure_system()
    tools = s["tools"].list_tools(category)
    return {"tools": [{"name": t.name, "category": t.category, "description": t.description,
                       "when_to_use": t.when_to_use, "dangerous": t.dangerous,
                       "parameters": [{"name": p.name, "type": p.type, "description": p.description,
                                       "required": p.required, "default": p.default} for p in t.parameters]} for t in tools]}


@app.post("/v2/tools/select")
def select_tools(req: ToolSelectRequest):
    s = _ensure_system()
    selections = s["tool_selector"].select(req.task, fast_mode=req.fast_mode)
    return {"task": req.task, "selections": selections}


@app.post("/v2/tools/run")
async def run_tools(req: ToolRunRequest):
    s = _ensure_system()
    results = await s["tool_executor"].run(req.selections, context=req.context)
    return {"results": results}


@app.post("/v2/tools/adaptive")
async def adaptive_run(req: GoalRequest):
    s = _ensure_system()
    selector = s["tool_selector"]
    executor = s["adaptive_executor"]

    # Select
    selections = selector.select(req.goal, fast_mode=False)
    nodes = executor.build_dag_from_selections(selections)

    # Execute DAG
    completed = await executor.run_dag(nodes)

    # ReAct
    react_nodes = []
    max_react = 2
    for _ in range(max_react):
        extra = executor.react_next_step(req.goal, completed)
        if not extra:
            break
        completed.append(extra)
        completed = await executor.run_dag(completed)
        react_nodes.append(extra.id)

    # Learn
    for node in completed:
        s["tool_memory"].record(
            task=req.goal,
            tool=node.tool,
            success=node.status == "done",
            latency_ms=0,
            output_summary=str(node.output)[:100]
        )

    report = executor.synthesize_report(completed, goal=req.goal)
    return {
        "goal": req.goal,
        "selections": [{"tool": s["tool"], "reason": s.get("reason", "")} for s in selections],
        "nodes": [{"id": n.id, "tool": n.tool, "status": n.status, "retries": n.retries,
                   "output": n.output} for n in completed],
        "react_nodes": react_nodes,
        "report": report,
    }


@app.get("/v2/tools/insights")
def tool_insights():
    s = _ensure_system()
    insights = s["tool_memory"].get_insights()
    return {"insights": insights, "total_records": len(s["tool_memory"].records)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("COGNITIVE_API_PORT", "8500")), log_level="info")


