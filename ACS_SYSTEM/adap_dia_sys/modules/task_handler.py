#!/usr/bin/env python3
"""
Task Handler.
Routes tasks to appropriate handlers based on task type.
"""
from typing import Any


def handle_task(task: str) -> dict[str, Any]:
    """Handle a task based on its type."""
    task_lower = task.lower()
    
    if "google" in task_lower:
        try:
            from modules.google_intergration import run_google_task
            return {"task": task, "status": "handled", "handler": "google"}
        except ImportError:
            return {"task": task, "status": "unavailable", "handler": "google"}
    
    elif "efficiency" in task_lower or "performance" in task_lower:
        try:
            from modules.learning.efficiency_engine import analyze_efficiency
            return {"task": task, "status": "handled", "handler": "efficiency"}
        except ImportError:
            return {"task": task, "status": "unavailable", "handler": "efficiency"}
    
    elif "govern" in task_lower or "decision" in task_lower:
        try:
            from modules.governance.decision_governor import enforce
            return {"task": task, "status": "handled", "handler": "governance"}
        except ImportError:
            return {"task": task, "status": "unavailable", "handler": "governance"}
    
    else:
        return {"task": task, "status": "no_handler", "message": "No known handler"}


def main():
    """CLI for testing."""
    import sys
    task = sys.argv[1] if len(sys.argv) > 1 else "default"
    result = handle_task(task)
    print(result)


if __name__ == "__main__":
    main()