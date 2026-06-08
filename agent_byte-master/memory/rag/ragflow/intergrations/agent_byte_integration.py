"""
Agent Byte Integration for GhostGoat — Production Grade

Hard dependency on Agent Byte core (torch, scikit-learn). If these are not
installed, this module will fail at import time. There is no fallback path,
no mock mode, and no placeholder behaviour.

Reward semantics:
    +1.0  task succeeded
    -1.0  task failed
    +0.5  bonus for fast execution (sub-linear in time)
    -0.05 penalty per step
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from agents.base import BaseAgent
from tools.registry import registry



# Event publishing for dashboard/diagnostics integration
try:
    from core.brain.adapters.agent_byte_events import event_publisher as _event_publisher
    _HAS_EVENTS = True
except Exception:
    _HAS_EVENTS = False
    _event_publisher = None

# Skill bridge — AgentByte learns feed into Agent-K cache
try:
    from core.bridges.agent_byte_skill_bridge import skill_bridge as _skill_bridge
    _HAS_SKILL_BRIDGE = True
except Exception:
    _HAS_SKILL_BRIDGE = False
    _skill_bridge = None

# Add near the top, after imports
# from brain.agent_core.startup import initialize_ghostgoat_brain

# In your __init__ or main startup function:
# dual_brain = initialize_ghostgoat_brain(orchestrator=self)



from vendor.agent_byte_master.core.agent import AgentByte
from vendor.agent_byte_master.core.config import AgentConfig
from vendor.agent_byte_master.core.interfaces import (
    ActionSpace,
    ActionSpaceType,
    Environment,
)
from vendor.agent_byte_master.storage.json_numpy_storage import JsonNumpyStorage

logger = logging.getLogger(__name__)

_STATE_DIM: int = 256
_MAX_STEPS_DEFAULT: int = 20
_REWARD_SUCCESS: float = 1.0
_REWARD_FAILURE: float = -1.0
_REWARD_STEP_PENALTY: float = -0.05
_REWARD_TIME_BONUS_BASE: float = 0.5


@dataclass
class TaskResult:
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_name: str = ""


class GhostGoatTaskEnvironment(Environment):
    def __init__(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        available_tools: Optional[List[str]] = None,
        max_steps: int = _MAX_STEPS_DEFAULT,
    ) -> None:
        self.task_description = task_description
        self.context = context or {}
        self.available_tools = available_tools or []
        self.max_steps = max_steps

        self._current_step: int = 0
        self._state: np.ndarray = np.zeros(_STATE_DIM, dtype=np.float32)
        self._done: bool = False
        self._info: Dict[str, Any] = {}
        self._cumulative_reward: float = 0.0
        self._last_action: int = 0
        self._last_reward: float = 0.0
        self._success_count: int = 0
        self._failure_count: int = 0
        self._task_embedding = self._embed_text(task_description)

    def reset(self) -> np.ndarray:
        self._current_step = 0
        self._done = False
        self._cumulative_reward = 0.0
        self._last_action = 0
        self._last_reward = 0.0
        self._success_count = 0
        self._failure_count = 0
        self._info = {"task": self.task_description, "steps": 0, "tools_used": []}
        self._state = self._build_state()
        return self._state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        self._current_step += 1
        self._last_action = int(action)

        reward, step_info = self._execute_action(int(action))
        self._last_reward = reward
        self._cumulative_reward += reward

        if reward > 0:
            self._success_count += 1
        elif reward < 0:
            self._failure_count += 1

        self._state = self._build_state()

        if int(action) == len(self.available_tools) + 1:
            self._done = True
        elif self._current_step >= self.max_steps:
            self._done = True

        self._info["steps"] = self._current_step
        self._info["cumulative_reward"] = self._cumulative_reward
        self._info.update(step_info)

        return self._state, reward, self._done, self._info

    def get_state_size(self) -> int:
        return _STATE_DIM

    def get_action_space(self) -> ActionSpace:
        n_tools = len(self.available_tools)
        size = n_tools + 2
        names = list(self.available_tools)
        names.extend(["reason", "terminate"])
        return ActionSpace(
            space_type=ActionSpaceType.DISCRETE,
            size=size,
            discrete_actions=names,
        )

    def get_id(self) -> str:
        return f"gg_task_{uuid.uuid5(uuid.NAMESPACE_OID, self.task_description)}"

    def _execute_action(self, action: int) -> Tuple[float, Dict[str, Any]]:
        n_tools = len(self.available_tools)

        if action == n_tools:
            return _REWARD_STEP_PENALTY, {"action": "reason"}

        if action == n_tools + 1:
            total = self._success_count + self._failure_count
            if total == 0:
                return _REWARD_FAILURE, {"action": "terminate", "ratio": 0.0}
            ratio = self._success_count / total
            return ratio * _REWARD_SUCCESS, {"action": "terminate", "ratio": ratio}

        if action < n_tools:
            tool_name = self.available_tools[action]
            start = time.perf_counter()
            result = self._invoke_tool(tool_name)
            elapsed = time.perf_counter() - start

            if result.success:
                time_bonus = _REWARD_TIME_BONUS_BASE * max(0.0, 1.0 - elapsed / 5.0)
                reward = _REWARD_SUCCESS + time_bonus + _REWARD_STEP_PENALTY
            else:
                reward = _REWARD_FAILURE + _REWARD_STEP_PENALTY

            info = {
                "action": "tool",
                "tool": tool_name,
                "success": result.success,
                "elapsed": round(elapsed, 4),
                "error": result.error,
            }
            self._info.setdefault("tools_used", []).append(tool_name)
            return reward, info

        return _REWARD_FAILURE, {"action": "invalid", "index": action}

    def _invoke_tool(self, tool_name: str) -> TaskResult:
        try:
            kwargs = self._build_tool_kwargs(tool_name)
            result = registry.execute_tool(tool_name, **kwargs)

            if result.success:
                return TaskResult(
                    success=True,
                    output=result.output,
                    execution_time=0.0,
                    tool_name=tool_name,
                )
            else:
                return TaskResult(
                    success=False,
                    output=None,
                    error=result.error or "Unknown error",
                    execution_time=0.0,
                    tool_name=tool_name,
                )
        except Exception as exc:
            logger.exception("Tool invocation failed: %s", tool_name)
            return TaskResult(
                success=False,
                output=None,
                error=str(exc),
                execution_time=0.0,
                tool_name=tool_name,
            )

    def _build_tool_kwargs(self, tool_name: str) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}

        if tool_name in ("list_directory", "file_scan"):
            kwargs["path"] = self.context.get("path", ".")
            kwargs["recursive"] = self.context.get("recursive", False)
        elif tool_name in ("port_scan",):
            kwargs["host"] = self.context.get("host", "localhost")
            kwargs["ports"] = self.context.get("ports", [80, 443, 22])
        elif tool_name in ("hash", "hash_compute"):
            kwargs["text"] = self.context.get("text", "")
            kwargs["algorithm"] = self.context.get("algorithm", "sha256")
        elif tool_name in ("http_request", "http_check"):
            kwargs["url"] = self.context.get("url", "")
            kwargs["method"] = self.context.get("method", "GET")
        elif tool_name in ("system_info",):
            pass
        else:
            kwargs = {k: v for k, v in self.context.items() if not k.startswith("_")}

        return kwargs

    def _build_state(self) -> np.ndarray:
        state = np.zeros(_STATE_DIM, dtype=np.float32)
        state[0:64] = self._task_embedding

        ctx_vec = self._encode_context()
        state[64:128] = ctx_vec

        action_one_hot = np.zeros(32, dtype=np.float32)
        if self._last_action < 32:
            action_one_hot[self._last_action] = 1.0
        state[128:160] = action_one_hot
        state[160] = np.clip(self._last_reward, -5.0, 5.0)
        state[161] = self._cumulative_reward / max(1, self._current_step)
        state[162] = self._success_count / max(1, self._current_step)
        state[163] = self._failure_count / max(1, self._current_step)

        state[192] = self._current_step / self.max_steps
        state[193] = len(self.available_tools) / 32.0
        state[194] = len(self._info.get("tools_used", [])) / max(1, len(self.available_tools))

        return state

    def _embed_text(self, text: str) -> np.ndarray:
        vec = np.zeros(64, dtype=np.float32)
        text = text.lower().strip()
        if not text:
            return vec

        for i in range(len(text) - 1):
            bigram = text[i:i + 2]
            bucket = hash(bigram) % 64
            vec[bucket] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _encode_context(self) -> np.ndarray:
        vec = np.zeros(64, dtype=np.float32)
        keys = list(self.context.keys())[:16]
        for i, key in enumerate(keys):
            idx = i * 2
            if idx + 1 >= 64:
                break
            vec[idx] = (hash(key) % 1000) / 1000.0
            val = self.context[key]
            if isinstance(val, (int, float)):
                vec[idx + 1] = np.clip(float(val) / 1000.0, -1.0, 1.0)
            elif isinstance(val, str):
                vec[idx + 1] = (hash(val) % 1000) / 1000.0
            elif isinstance(val, bool):
                vec[idx + 1] = 1.0 if val else 0.0
        return vec


class AgentByteAgent(BaseAgent):
    def __init__(
        self,
        agent_id: Optional[str] = None,
        storage_path: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ) -> None:
        super().__init__(agent_id)
        self._storage_path = storage_path or f"./data/agent_byte/{self.agent_id}"
        self._config = config
        self._training_log: List[Dict[str, Any]] = []
        self._total_episodes: int = 0

        storage = JsonNumpyStorage(self._storage_path)
        self._byte = AgentByte(
            agent_id=self.agent_id,
            storage=storage,
            config=config,
            enable_checkpointing=True,
        )
        logger.info("AgentByte agent %s initialised", self.agent_id)

    @property
    def name(self) -> str:
        return "AgentByte"

    @property
    def description(self) -> str:
        return (
            "Neural-symbolic RL agent with transfer learning. "
            "Learns optimal task execution strategies through real experience."
        )

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.update_state(status="executing", current_task=task)
        ctx = context or {}

        env = GhostGoatTaskEnvironment(
            task_description=task,
            context=ctx,
            available_tools=ctx.get("available_tools", []),
            max_steps=ctx.get("max_steps", _MAX_STEPS_DEFAULT),
        )

        if _HAS_EVENTS and _event_publisher:
            _event_publisher.episode_start(task, self.agent_id)

        try:
            result_summary = self._train_episode(env, task)
            self.state.tasks_completed += 1
            self.update_state(status="completed")

            if _HAS_EVENTS and _event_publisher:
                info = env._info
                _event_publisher.episode_complete(
                    task, self.agent_id,
                    info.get("cumulative_reward", 0.0),
                    info.get("steps", 0),
                    info.get("tools_used", []),
                )

            return result_summary
        except Exception as exc:
            logger.error("AgentByte execution failed: %s", exc)
            self.update_state(status="failed", error=str(exc))

            if _HAS_EVENTS and _event_publisher:
                _event_publisher.training_failed(task, self.agent_id, str(exc))

            raise

    def _train_episode(self, env: GhostGoatTaskEnvironment, task: str) -> str:
        self._byte.train(env, episodes=1)
        self._total_episodes += 1

        info = env._info
        steps = info.get("steps", 0)
        cumulative = info.get("cumulative_reward", 0.0)
        tools_used = info.get("tools_used", [])
        last_action = info.get("action", "unknown")

        self._training_log.append(
            {
                "task": task,
                "steps": steps,
                "reward": cumulative,
                "tools": tools_used,
                "timestamp": time.time(),
            }
        )

        summary = (
            f"[AgentByte] Task complete. "
            f"Episodes={self._total_episodes} "
            f"Steps={steps} "
            f"Reward={cumulative:.3f} "
            f"Tools={tools_used} "
            f"LastAction={last_action}"
        )
        logger.info(summary)
        return summary

    def execute_policy(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.update_state(status="executing", current_task=task)
        ctx = context or {}

        env = GhostGoatTaskEnvironment(
            task_description=task,
            context=ctx,
            available_tools=ctx.get("available_tools", []),
            max_steps=ctx.get("max_steps", _MAX_STEPS_DEFAULT),
        )

        state = env.reset()
        total_reward = 0.0
        steps = 0
        actions_taken: List[str] = []

        done = False
        while not done and steps < env.max_steps:
            if self._byte.dual_brain is None:
                raise RuntimeError(
                    "AgentByte dual_brain not initialised — "
                    "train on at least one task before inference."
                )

            normalised = self._byte.state_normalizer.normalize(state)
            action = self._byte.dual_brain.act(normalised, deterministic=True)

            state, reward, done, info = env.step(action)
            total_reward += reward
            steps += 1
            actions_taken.append(info.get("action", str(action)))

        self.state.tasks_completed += 1
        self.update_state(status="completed")

        summary = (
            f"[AgentByte] Inference complete. "
            f"Steps={steps} "
            f"Reward={total_reward:.3f} "
            f"Actions={actions_taken}"
        )
        logger.info(summary)
        return summary

    def transfer_to_domain(self, target_task_type: str, sample_tools: List[str]) -> str:
        env = GhostGoatTaskEnvironment(
            task_description=f"transfer_target:{target_task_type}",
            available_tools=sample_tools,
        )
        self._byte.transfer_to(env)
        return f"Knowledge transferred to domain: {target_task_type}"

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            **self.to_dict(),
            "total_episodes": self._total_episodes,
            "training_entries": len(self._training_log),
            "recent_rewards": [e["reward"] for e in self._training_log[-10:]],
            "recent_tools": [e["tools"] for e in self._training_log[-10:]],
            "agent_byte_id": self._byte.agent_id,
            "environments_experienced": list(self._byte.environments_experienced),
            "storage_path": self._storage_path,
        }
        return stats


class AgentByteCapability:
    RL = "reinforcement_learning"
    TRANSFER = "transfer_learning"
    OPTIMISATION = "task_optimisation"


def register_agent_byte(
    orchestrator: Any,
    agent_id: Optional[str] = None,
    storage_path: Optional[str] = None,
    config: Optional[AgentConfig] = None,
) -> AgentByteAgent:
    agent = AgentByteAgent(
        agent_id=agent_id,
        storage_path=storage_path,
        config=config,
    )

    if hasattr(orchestrator, "agent_network"):
        network = orchestrator.agent_network
        if hasattr(network, "agents") and isinstance(network.agents, dict):
            network.agents[agent.agent_id] = {
                "host": "127.0.0.1",
                "port": 0,
                "type": "agent_byte",
                "capabilities": [
                    AgentByteCapability.RL,
                    AgentByteCapability.TRANSFER,
                    AgentByteCapability.OPTIMISATION,
                ],
            }
            logger.info("AgentByte %s registered in agent_network", agent.agent_id)

    if hasattr(orchestrator, "_local_agents") and isinstance(
        orchestrator._local_agents, dict
    ):
        orchestrator._local_agents[agent.agent_id] = agent
        logger.info("AgentByte %s registered in _local_agents", agent.agent_id)

    if hasattr(orchestrator, "register_capability"):
        orchestrator.register_capability(
            agent_id=agent.agent_id,
            capabilities=[
                AgentByteCapability.RL,
                AgentByteCapability.TRANSFER,
                AgentByteCapability.OPTIMISATION,
            ],
            agent=agent,
        )

    logger.info("AgentByte agent %s fully registered with orchestrator", agent.agent_id)
    return agent
