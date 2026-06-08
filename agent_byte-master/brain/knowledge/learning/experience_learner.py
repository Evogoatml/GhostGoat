"""
Experience Learner for Agent Byte.
Manages episodic memory and experience replay.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np


class Experience:
    """Single transition experience."""

    def __init__(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        info: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.state = state
        self.action = action
        self.reward = reward
        self.next_state = next_state
        self.done = done
        self.info = info or {}


class ExperienceLearner:
    """Episodic memory with prioritized replay support."""

    def __init__(self, capacity: int = 10000) -> None:
        self.capacity = capacity
        self.buffer: List[Experience] = []
        self.position = 0

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add experience to buffer."""
        exp = Experience(state, action, reward, next_state, done, info)
        if len(self.buffer) < self.capacity:
            self.buffer.append(exp)
        else:
            self.buffer[self.position] = exp
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Experience]:
        """Random sample of experiences."""
        if len(self.buffer) < batch_size:
            return self.buffer.copy()
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        return [self.buffer[i] for i in indices]

    def get_recent(self, n: int = 100) -> List[Experience]:
        """Get n most recent experiences."""
        return self.buffer[-n:]

    def size(self) -> int:
        return len(self.buffer)

    def clear(self) -> None:
        self.buffer.clear()
        self.position = 0
