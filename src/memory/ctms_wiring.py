"""GhostGoat ↔ CTMS wiring — the stable seam between the two systems.

``ctms_liquid.py`` is a pure, dependency-free library. This module is the ONLY
place that knows about both it and GhostGoat's ``LLMGateway``. If either side
ever changes, only this file adapts — nothing else in the codebase needs to.

Components:
    _AsyncBridge      call the async gateway from sync CTMS code, safe even
                      when invoked inside a running event loop (dedicated
                      thread + own loop — one uniform code path).
    StableExpander    LLM-driven expansion with a deterministic fallback —
                      expand() never raises, so task execution can't break.
    build_ctms_mapper factory used by the orchestrator; duck-types the gateway
                      (anything with ``async complete(prompt, system=None)``).
"""
import asyncio
import logging
import socket
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, List, Optional

from src.memory.ctms_liquid import (
    Expander,
    LLMExpander,
    LiquidS4Expander,
    ThoughtMapper,
    ThoughtNode,
)

logger = logging.getLogger("ghostgoat.ctms.wiring")

LLM_CALL_TIMEOUT = 120.0  # generous: gateway already retries rate limits internally


class _AsyncBridge:
    """Call an async function from sync code — safe inside or outside a loop.

    Always uses a dedicated daemon thread with its own event loop, so there is
    exactly one code path regardless of the caller's context (sync script,
    FastAPI handler, orchestrator coroutine).
    """

    def __init__(self, coro_fn: Callable[..., Any], timeout: float = LLM_CALL_TIMEOUT):
        self._fn = coro_fn
        self._timeout = timeout
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()

    def __call__(self, prompt: str, system: Optional[str] = None) -> str:
        with self._lock:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                threading.Thread(
                    target=self._loop.run_forever,
                    daemon=True,
                    name="ctms-llm-bridge",
                ).start()
            future = asyncio.run_coroutine_threadsafe(self._fn(prompt, system), self._loop)
        return future.result(self._timeout)


class StableExpander:
    """Primary expander with a deterministic fallback — expand() never raises.

    A full fallback (rather than per-step) keeps behavior simple and
    content-addressed IDs make a later retry safe: re-running after an
    outage adds only genuinely new steps.
    """

    def __init__(self, primary: Expander, fallback: Optional[Expander] = None):
        self.primary = primary
        self.fallback = fallback or LiquidS4Expander()

    def expand(self, seed: str, depth: int = 10) -> List[ThoughtNode]:
        try:
            chain = self.primary.expand(seed, depth)
            if chain:
                return chain
            logger.warning("primary expander returned an empty chain; using fallback")
        except Exception:
            logger.exception("primary expander failed; using deterministic fallback")
        return self.fallback.expand(seed, depth)


def _default_replica_id() -> str:
    """Stable per-machine replica id (survives restarts, distinct across hosts)."""
    try:
        return f"{socket.gethostname()}-{uuid.getnode():x}"
    except Exception:
        return str(uuid.uuid4())[:8]


def build_ctms_mapper(
    llm: Any,
    path: str | Path,
    replica_id: Optional[str] = None,
) -> ThoughtMapper:
    """Build a ThoughtMapper whose expander is the live GhostGoat LLM gateway.

    ``llm`` is duck-typed: anything exposing ``async complete(prompt, system=None)``
    works — the real ``LLMGateway`` or a test fake.
    """
    bridge = _AsyncBridge(llm.complete)
    expander = StableExpander(LLMExpander(complete=bridge))
    return ThoughtMapper(
        path=str(path),
        replica_id=replica_id or _default_replica_id(),
        expander=expander,
    )
