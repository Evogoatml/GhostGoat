# Lazy imports to avoid initialization issues

def memory():
    from core.controllers.memory_controller import memory
    return memory

def llm():
    from core.controllers.llm_controller import llm
    return llm

def tools():
    from core.controllers.tool_controller import tools
    return tools

def task_ctrl():
    from core.controllers.task_controller import task_ctrl
    return task_ctrl

# Keep these for backwards compatibility
MemoryController = None
LLMController = None
ToolController = None
TaskController = None
Task = None
Priority = None

__all__ = [
    "memory", "llm", "tools", "task_ctrl",
    "MemoryController", "LLMController", "ToolController",
    "TaskController", "Task", "Priority",
]
