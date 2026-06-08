
"""
Agent Byte Health Monitor.

Plugs into GhostGoat's diagnostic system to monitor:
- Training success rate
- Average reward per episode
- Tool usage patterns
- AgentByte core health
"""

import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AgentByteMonitor:
    """
    Monitors AgentByte health and reports to the diagnostic center.
    """

    def __init__(self, agent_byte=None):
        self._agent = agent_byte
        self._last_check = 0.0
        self._check_interval = 30.0  # seconds
        self._history: List[Dict[str, Any]] = []

    def check(self) -> Dict[str, Any]:
        """
        Run a health check on AgentByte.
        Returns diagnostic report dict.
        """
        now = time.time()
        if now - self._last_check < self._check_interval:
            return self._history[-1] if self._history else {}

        self._last_check = now
        report = {
            "timestamp": now,
            "component": "agent_byte",
            "healthy": True,
            "checks": {},
        }

        if self._agent is None:
            report["healthy"] = False
            report["checks"]["initialised"] = False
            return report

        try:
            stats = self._agent.get_stats()
            report["checks"]["initialised"] = True
            report["checks"]["agent_id"] = stats.get("agent_id", "unknown")
            report["checks"]["total_episodes"] = stats.get("total_episodes", 0)
            report["checks"]["recent_rewards"] = stats.get("recent_rewards", [])

            # Health rules
            recent = stats.get("recent_rewards", [])
            if recent:
                avg_reward = sum(recent) / len(recent)
                report["checks"]["avg_recent_reward"] = round(avg_reward, 3)
                if avg_reward < -0.5:
                    report["healthy"] = False
                    report["checks"]["reward_degradation"] = True

            if stats.get("total_episodes", 0) == 0:
                report["checks"]["untrained"] = True

        except Exception as exc:
            report["healthy"] = False
            report["checks"]["error"] = str(exc)
            logger.error("AgentByte health check failed: %s", exc)

        self._history.append(report)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return report

    def get_history(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._history[-n:]
