
"""
Agent Byte → Skill Library Bridge.

When AgentByte learns a successful strategy, it feeds into GhostGoat's
Agent-K skill cache so all agents benefit from its experience.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from core.brain.agents.tool_agent import tool_agent as skill_library as _skill_library
    _HAS_SKILLS = True
except Exception:
    _HAS_SKILLS = False
    _skill_library = None


class AgentByteSkillBridge:
    """
    Bridges AgentByte training episodes into the GhostGoat skill library.
    """

    def __init__(self, skill_library=None):
        self._library = skill_library or _skill_library
        self._enabled = _HAS_SKILLS and self._library is not None

    def record_episode(self, task: str, tools_used: list, reward: float, steps: int) -> bool:
        """
        Record a successful episode as a skill in the library.
        Only records if reward is positive (successful strategy).
        """
        if not self._enabled:
            return False

        if reward <= 0:
            return False  # Only cache successful strategies

        try:
            # Build a skill entry compatible with Agent-K
            skill_key = f"agent_byte:{task.split()[0]}"
            skill_entry = {
                "task_pattern": task,
                "tools": tools_used,
                "reward": reward,
                "steps": steps,
                "source": "agent_byte",
                "confidence": min(1.0, max(0.0, reward / 5.0)),
            }

            # Inject into skill library
            if hasattr(self._library, "add_skill"):
                self._library.add_skill(skill_key, skill_entry)
            elif hasattr(self._library, "cache"):
                self._library.cache(skill_key, skill_entry)

            logger.info("AgentByte skill cached: %s (reward=%.3f)", skill_key, reward)
            return True

        except Exception as exc:
            logger.warning("Failed to cache AgentByte skill: %s", exc)
            return False

    def lookup(self, task: str) -> Optional[Dict[str, Any]]:
        """Look up a previously learned strategy for a task."""
        if not self._enabled:
            return None

        try:
            skill_key = f"agent_byte:{task.split()[0]}"
            if hasattr(self._library, "lookup"):
                return self._library.lookup(skill_key)
            elif hasattr(self._library, "get"):
                return self._library.get(skill_key)
        except Exception:
            pass
        return None


# Global bridge instance
skill_bridge = AgentByteSkillBridge()
