
"""
Agent Byte API Endpoints for GhostGoat FastAPI server.

Provides:
  POST /agent-byte/train   — Train AgentByte on a task
  POST /agent-byte/infer   — Run inference with learned policy
  GET  /agent-byte/stats   — Get agent statistics
  GET  /agent-byte/health  — Health check
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-byte", tags=["agent-byte"])


class TrainRequest(BaseModel):
    task: str
    context: Dict[str, Any] = {}
    available_tools: List[str] = []
    max_steps: int = 20


class InferRequest(BaseModel):
    task: str
    context: Dict[str, Any] = {}
    available_tools: List[str] = []
    max_steps: int = 20


class AgentByteResponse(BaseModel):
    success: bool
    result: str
    agent_id: str
    stats: Dict[str, Any]


# Lazy-loaded agent reference — set by main app
_agent_byte = None

def set_agent_byte(agent):
    global _agent_byte
    _agent_byte = agent
    logger.info("AgentByte API router wired to agent %s", agent.agent_id)


@router.post("/train", response_model=AgentByteResponse)
async def train_agent(request: TrainRequest):
    """Train AgentByte on a single task episode."""
    if _agent_byte is None:
        raise HTTPException(status_code=503, detail="AgentByte not initialised")
    try:
        result = _agent_byte.execute(
            request.task,
            {
                "available_tools": request.available_tools,
                "max_steps": request.max_steps,
                **request.context,
            },
        )
        return AgentByteResponse(
            success=True,
            result=result,
            agent_id=_agent_byte.agent_id,
            stats=_agent_byte.get_stats(),
        )
    except Exception as exc:
        logger.exception("AgentByte train failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/infer", response_model=AgentByteResponse)
async def infer_agent(request: InferRequest):
    """Run inference using learned policy (no training)."""
    if _agent_byte is None:
        raise HTTPException(status_code=503, detail="AgentByte not initialised")
    try:
        result = _agent_byte.execute_policy(
            request.task,
            {
                "available_tools": request.available_tools,
                "max_steps": request.max_steps,
                **request.context,
            },
        )
        return AgentByteResponse(
            success=True,
            result=result,
            agent_id=_agent_byte.agent_id,
            stats=_agent_byte.get_stats(),
        )
    except Exception as exc:
        logger.exception("AgentByte inference failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stats")
async def get_stats():
    """Get AgentByte statistics."""
    if _agent_byte is None:
        raise HTTPException(status_code=503, detail="AgentByte not initialised")
    return {
        "success": True,
        "agent_id": _agent_byte.agent_id,
        "stats": _agent_byte.get_stats(),
    }


@router.get("/health")
async def health():
    """AgentByte health check."""
    return {
        "status": "healthy" if _agent_byte else "unavailable",
        "agent_id": _agent_byte.agent_id if _agent_byte else None,
    }
