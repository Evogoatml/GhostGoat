"""Runtime governance: bound task execution in time, concurrency and spend.

``decision_governor`` answers "may this CLASS of action run at all" (policy).
``TaskGovernor`` answers "may ANOTHER task run RIGHT NOW" — rate windows,
concurrency caps, a daily budget and stale-task identification, all
env-configurable with safe defaults:

    GHOSTGOAT_MAX_CONCURRENT_TASKS   (default 3)
    GHOSTGOAT_TASKS_PER_MINUTE       (default 5, per chat/source)
    GHOSTGOAT_DAILY_TASK_BUDGET      (default 200, 0 = unlimited)
    GHOSTGOAT_TASK_TIMEOUT           (default 180 seconds, 0 = unlimited)

Admission is non-blocking: when a limit is hit the caller gets an honest
status ("busy" / "rate_limited" / "budget_exhausted") instead of an
unbounded queue.
"""

import os
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class TaskGovernor:
    """Admission control for task execution."""

    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        tasks_per_minute: Optional[int] = None,
        daily_budget: Optional[int] = None,
        task_timeout: Optional[int] = None,
    ):
        self.max_concurrent = max_concurrent if max_concurrent is not None else _env_int("GHOSTGOAT_MAX_CONCURRENT_TASKS", 3)
        self.tasks_per_minute = tasks_per_minute if tasks_per_minute is not None else _env_int("GHOSTGOAT_TASKS_PER_MINUTE", 5)
        self.daily_budget = daily_budget if daily_budget is not None else _env_int("GHOSTGOAT_DAILY_TASK_BUDGET", 200)
        self.task_timeout = task_timeout if task_timeout is not None else _env_int("GHOSTGOAT_TASK_TIMEOUT", 180)
        self.chats_per_minute = _env_int("GHOSTGOAT_CHATS_PER_MINUTE", 20)
        self._lock = threading.Lock()
        self._running = 0
        self._windows: Dict[str, Deque[float]] = {}
        self._chat_windows: Dict[str, Deque[float]] = {}
        self._budget_day = ""
        self._budget_used = 0

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def try_acquire(self, source: str = "api") -> Tuple[bool, str]:
        """Non-blocking admission check. On True the caller MUST release()."""
        now = time.time()
        with self._lock:
            today = self._today()
            if today != self._budget_day:
                self._budget_day = today
                self._budget_used = 0
            if self.daily_budget > 0 and self._budget_used >= self.daily_budget:
                return False, "budget_exhausted"

            window = self._windows.setdefault(source, deque())
            cutoff = now - 60.0
            while window and window[0] < cutoff:
                window.popleft()
            if self.tasks_per_minute > 0 and len(window) >= self.tasks_per_minute:
                return False, "rate_limited"

            if self.max_concurrent > 0 and self._running >= self.max_concurrent:
                return False, "busy"

            window.append(now)
            self._running += 1
            return True, "allowed"

    def allow_chat(self, source: str = "api") -> bool:
        """Rate-window admission for casual chat replies.

        Chat is one bounded LLM call — no concurrency slot, no budget charge,
        but its own higher window (GHOSTGOAT_CHATS_PER_MINUTE, default 20/min).
        """
        if self.chats_per_minute <= 0:
            return True
        now = time.time()
        with self._lock:
            window = self._chat_windows.setdefault(source, deque())
            cutoff = now - 60.0
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= self.chats_per_minute:
                return False
            window.append(now)
            return True

    def release(self) -> None:
        with self._lock:
            self._running = max(0, self._running - 1)

    def record_outcome(self) -> None:
        """Count one finished task against the daily budget."""
        with self._lock:
            today = self._today()
            if today != self._budget_day:
                self._budget_day = today
                self._budget_used = 0
            self._budget_used += 1

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "max_concurrent": self.max_concurrent,
                "tasks_per_minute": self.tasks_per_minute,
                "daily_budget": self.daily_budget,
                "daily_used": self._budget_used,
                "task_timeout": self.task_timeout,
                "chats_per_minute": self.chats_per_minute,
            }

    @staticmethod
    def find_stale(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Tasks stuck in 'running' — e.g. left behind by a crashed process."""
        return [t for t in tasks if t.get("status") == "running"]
