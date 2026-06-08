# core/governance/task_handler.py
"""Legacy task handler — delegates to core.task_handler."""

from core.governance.task_handler import handle_task, handle_task_async

__all__ = ["handle_task", "handle_task_async"]
