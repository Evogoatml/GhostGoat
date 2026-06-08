
"""
Agent Byte Event Publisher.

Publishes AgentByte lifecycle events to the GhostGoat event bus.
"""

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

try:
    from core.bus.event_bus import event_bus as _event_bus
    _HAS_BUS = True
except Exception:
    _HAS_BUS = False
    _event_bus = None


class AgentByteEventPublisher:
    EVENT_NAMESPACE = "agent_byte"

    def __init__(self, bus=None):
        self._bus = bus or _event_bus
        self._enabled = _HAS_BUS and self._bus is not None

    def _emit(self, event_type: str, payload: Dict[str, Any]) -> bool:
        if not self._enabled:
            return False
        try:
            event = {
                "namespace": self.EVENT_NAMESPACE,
                "type": event_type,
                "timestamp": time.time(),
                "payload": payload,
            }
            if hasattr(self._bus, "publish"):
                self._bus.publish(f"{self.EVENT_NAMESPACE}.{event_type}", event)
            return True
        except Exception as exc:
            logger.debug("Event publish failed: %s", exc)
            return False

    def episode_start(self, task: str, agent_id: str) -> bool:
        return self._emit("episode_start", {"task": task, "agent_id": agent_id})

    def episode_complete(self, task: str, agent_id: str, reward: float, steps: int, tools: list) -> bool:
        return self._emit("episode_complete", {
            "task": task, "agent_id": agent_id,
            "reward": reward, "steps": steps, "tools": tools,
        })

    def training_failed(self, task: str, agent_id: str, error: str) -> bool:
        return self._emit("training_failed", {"task": task, "agent_id": agent_id, "error": error})

    def inference_complete(self, task: str, agent_id: str, reward: float, steps: int) -> bool:
        return self._emit("inference_complete", {
            "task": task, "agent_id": agent_id, "reward": reward, "steps": steps,
        })


event_publisher = AgentByteEventPublisher()
