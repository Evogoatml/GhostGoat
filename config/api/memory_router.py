"""Authenticated read-only API over the ThoughtStore-backed memory."""
import hmac
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from run_cognitive_system import get_orchestrator

API_KEY_ENV = "GHOSTGOAT_API_KEY"


def require_api_key(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
) -> None:
    expected = os.getenv(API_KEY_ENV, "")
    if not expected:
        raise HTTPException(status_code=503, detail="Memory API disabled: API key not configured")
    supplied = x_api_key or ""
    if not supplied and authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


router = APIRouter(prefix="/api/thoughts", tags=["memory"], dependencies=[Depends(require_api_key)])


@router.get("/roots")
def list_roots(limit: int = 100):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
    roots = get_orchestrator().thoughts.roots(limit)
    return {"roots": roots, "count": len(roots)}


@router.get("/roots/{root_id}/tree")
def get_tree(root_id: str):
    tree = get_orchestrator().thoughts.tree(root_id)
    if tree is None:
        raise HTTPException(status_code=404, detail="Root thought not found")
    return tree


@router.get("/{thought_id}")
def get_record(thought_id: str):
    record = get_orchestrator().thoughts.get(thought_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Thought not found")
    return record
