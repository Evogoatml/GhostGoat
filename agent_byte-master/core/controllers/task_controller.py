"""
TaskController — priority task queue and routing for the whole system.
Agents submit tasks here; the controller routes them to the right agent
based on domain and priority. Tracks every task from submission to completion.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3


@dataclass
class Task:
    description: str
    domain: str = "general"
    priority: Priority = Priority.NORMAL
    context: Dict[str, Any] = field(default_factory=dict)
    submitted_by: str = "system"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "queued"        # queued | running | done | failed
    result: Optional[Any] = None
    error: Optional[str] = None


class TaskController:
    """
    Central task queue.  Agents or the Telegram bot submit tasks;
    the controller routes them to the registered executor and tracks
    them through completion.
    """

    _instance: Optional["TaskController"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    def __init__(self):
        if self._ready:
            return
        # asyncio.PriorityQueue: (priority, task)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._history: List[Task] = []
        self._executor: Optional[Callable] = None   # set by SystemBootstrapper
        self._running = False
        self._ready = True

    def set_executor(self, executor: Callable):
        """Register the function that actually runs tasks (e.g. orchestrator.execute_async)."""
        self._executor = executor

    async def submit(self, task: Task) -> str:
        """Add task to queue. Returns task id."""
        await self._queue.put((task.priority, task))
        self._history.append(task)
        logger.info("[TaskCtrl] submitted %s (domain=%s pri=%s)", task.id[:8], task.domain, task.priority.name)
        return task.id

    def submit_sync(self, task: Task) -> str:
        """Synchronous submit — creates a new event loop if needed."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.submit(task))
                self._history.append(task)
                return task.id
            return loop.run_until_complete(self.submit(task))
        except Exception:
            self._history.append(task)
            return task.id

    async def run_loop(self):
        """
        Continuous processing loop.  Call once at startup; runs forever.
        Tasks are picked off the queue and dispatched to the executor.
        """
        self._running = True
        logger.info("[TaskCtrl] loop started")
        while self._running:
            try:
                _, task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("[TaskCtrl] queue error: %s", e)
                continue

            task.status = "running"
            logger.info("[TaskCtrl] running %s", task.id[:8])
            try:
                if self._executor:
                    goal = {"description": task.description, "domain": task.domain,
                            "context": task.context}
                    result = await self._executor(goal)
                    task.result = result
                    task.status = "done"
                else:
                    task.status = "failed"
                    task.error = "No executor registered"
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                logger.error("[TaskCtrl] task %s failed: %s", task.id[:8], e)
            finally:
                self._queue.task_done()

    def stop(self):
        self._running = False

    def get_task(self, task_id: str) -> Optional[Task]:
        return next((t for t in self._history if t.id == task_id), None)

    def recent(self, n: int = 20) -> List[Dict]:
        return [
            {"id": t.id[:8], "description": t.description[:60],
             "status": t.status, "domain": t.domain}
            for t in self._history[-n:]
        ]


# Singleton
task_ctrl = TaskController()
