"""
GhostGoat Tool Intelligence Layer — Merged with existing architecture.
Exports both the new intelligence layer and maintains backward compatibility.
"""
# New tool intelligence layer
from .tool_registry import ToolRegistry, Tool, ToolParameter
from .tool_selector import ToolSelector
from .tool_executor import ToolExecutor
from .adaptive_executor import AdaptiveExecutor, ExecutionNode
from .tool_memory import ToolMemory

# Keep existing imports available
__all__ = [
    "ToolRegistry", "Tool", "ToolParameter",
    "ToolSelector", "ToolExecutor", "AdaptiveExecutor", "ExecutionNode",
    "ToolMemory",
]

