
"""
Telegram Bot Extensions for AgentByte.

Adds commands:
  /train <task>       — Train AgentByte on a task
  /infer <task>       — Run AgentByte inference
  /byte_stats         — Show AgentByte statistics
  /byte_health        — Health check
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from core.brain.agents.agent_byte_integration import AgentByteAgent
    _HAS_AGENT_BYTE = True
except Exception:
    _HAS_AGENT_BYTE = False
    AgentByteAgent = None


class TelegramAgentByteHandler:
    """Telegram command handler for AgentByte operations."""

    def __init__(self, agent: Optional[AgentByteAgent] = None):
        self._agent = agent

    def _get_agent(self):
        if self._agent is None and _HAS_AGENT_BYTE:
            # Lazy init
            self._agent = AgentByteAgent(agent_id="telegram_agent_byte")
        return self._agent

    def cmd_train(self, task: str, context: Optional[dict] = None) -> str:
        """Handle /train command."""
        agent = self._get_agent()
        if agent is None:
            return "AgentByte not available"

        try:
            ctx = context or {}
            result = agent.execute(task, ctx)
            stats = agent.get_stats()
            return (
                f"AgentByte Training Result:\n\n"
                f"{result}\n\n"
                f"Episodes: {stats.get("total_episodes", 0)}\n"
                f"Tasks Completed: {stats.get("tasks_completed", 0)}\n"
                f"Recent Rewards: {stats.get("recent_rewards", [])}"
            )
        except Exception as exc:
            logger.exception("Telegram train failed")
            return f"Training error: {exc}"

    def cmd_infer(self, task: str, context: Optional[dict] = None) -> str:
        """Handle /infer command."""
        agent = self._get_agent()
        if agent is None:
            return "AgentByte not available"

        try:
            ctx = context or {}
            result = agent.execute_policy(task, ctx)
            return f"AgentByte Inference:\n\n{result}"
        except Exception as exc:
            return f"Inference error: {exc}"

    def cmd_stats(self) -> str:
        """Handle /byte_stats command."""
        agent = self._get_agent()
        if agent is None:
            return "AgentByte not available"

        stats = agent.get_stats()
        lines = [
            "AgentByte Statistics",
            "=====================",
            f"Agent ID: {stats.get("agent_id", "unknown")}",
            f"Status: {stats.get("status", "unknown")}",
            f"Episodes: {stats.get("total_episodes", 0)}",
            f"Tasks Completed: {stats.get("tasks_completed", 0)}",
            f"Recent Rewards: {stats.get("recent_rewards", [])}",
            f"Environments: {len(stats.get("environments_experienced", []))}",
        ]
        return "\n".join(lines)

    def cmd_health(self) -> str:
        """Handle /byte_health command."""
        agent = self._get_agent()
        if agent is None:
            return "AgentByte: UNAVAILABLE"

        stats = agent.get_stats()
        healthy = stats.get("total_episodes", 0) > 0
        status = "HEALTHY" if healthy else "UNTRAINED"
        return f"AgentByte: {status}"


# Global handler
telegram_byte_handler = TelegramAgentByteHandler()
