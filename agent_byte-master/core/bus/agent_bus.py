"""
AgentBus — real-time message passing between all agents.

Every agent can publish messages and subscribe to topics.
Built on asyncio queues internally; exposes a WebSocket server
so external processes (dashboard, tools) can also connect.

Topics
------
  task.new          A new task was submitted
  task.done         A task completed
  agent.thinking    An agent is reasoning (debug stream)
  agent.result      An agent produced a result
  memory.stored     Something was written to memory
  godel.critique    PMMAGO Gödel critic fired
  system.status     Heartbeat / system state

Usage
-----
    from core.bus.agent_bus import bus

    # Subscribe
    async def handler(msg): print(msg)
    bus.subscribe("task.done", handler)

    # Publish
    await bus.publish("task.new", {"task": "analyze churn", "domain": "analysis"})
"""
from __future__ import annotations
import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentBus:
    """Central async pub/sub message bus."""

    _instance: Optional["AgentBus"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    def __init__(self):
        if self._ready:
            return
        # topic -> list of async handlers
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        # full message log (capped)
        self._log: List[Dict] = []
        self._log_max = 1000
        # wildcard subscribers (receive everything)
        self._wildcard: List[Callable] = []
        self._ws_connections: List[Any] = []  # websocket connections
        self._ready = True

    # ── subscribe ─────────────────────────────────────────────────────────────

    def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe handler to a topic. Use topic='*' for all messages."""
        if topic == "*":
            self._wildcard.append(handler)
        else:
            self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        if topic == "*":
            self._wildcard = [h for h in self._wildcard if h != handler]
        else:
            self._subscribers[topic] = [h for h in self._subscribers[topic] if h != handler]

    # ── publish ───────────────────────────────────────────────────────────────

    async def publish(self, topic: str, data: Any, source: str = "system") -> None:
        """Publish a message. Delivers to all subscribers and WebSocket clients."""
        msg = {
            "topic": topic,
            "data": data,
            "source": source,
            "ts": datetime.utcnow().isoformat(),
        }
        # Log
        self._log.append(msg)
        if len(self._log) > self._log_max:
            self._log = self._log[-self._log_max:]

        # Deliver to topic subscribers
        handlers = list(self._subscribers.get(topic, []))
        handlers += self._wildcard

        for handler in handlers:
            try:
                result = handler(msg)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning("[Bus] handler error on %s: %s", topic, e)

        # Forward to WebSocket clients
        if self._ws_connections:
            payload = json.dumps(msg, default=str)
            dead = []
            for ws in self._ws_connections:
                try:
                    await ws.send(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._ws_connections.remove(ws)

    def publish_sync(self, topic: str, data: Any, source: str = "system") -> None:
        """Fire-and-forget publish from synchronous code."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.publish(topic, data, source))
            else:
                loop.run_until_complete(self.publish(topic, data, source))
        except Exception as e:
            logger.debug("[Bus] publish_sync error: %s", e)

    # ── WebSocket server ──────────────────────────────────────────────────────

    async def start_ws_server(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Start a WebSocket server so dashboards/tools can subscribe to the bus.
        Any connected client receives every message published on any topic.
        """
        try:
            import websockets
            async def handler(ws, path=None):
                self._ws_connections.append(ws)
                logger.info("[Bus] WebSocket client connected from %s", ws.remote_address)
                try:
                    # Send backlog of last 50 messages on connect
                    for msg in self._log[-50:]:
                        await ws.send(json.dumps(msg, default=str))
                    await ws.wait_closed()
                finally:
                    if ws in self._ws_connections:
                        self._ws_connections.remove(ws)

            server = await websockets.serve(handler, host, port)
            logger.info("[Bus] WebSocket server on ws://%s:%d", host, port)
            return server
        except ImportError:
            logger.warning("[Bus] websockets not installed — WS server disabled")
        except Exception as e:
            logger.warning("[Bus] WS server failed to start: %s", e)

    # ── inspection ────────────────────────────────────────────────────────────

    def recent(self, n: int = 20, topic: Optional[str] = None) -> List[Dict]:
        if topic:
            msgs = [m for m in self._log if m["topic"] == topic]
        else:
            msgs = self._log
        return msgs[-n:]

    def topics(self) -> List[str]:
        return list(self._subscribers.keys())


# Singleton
bus = AgentBus()
