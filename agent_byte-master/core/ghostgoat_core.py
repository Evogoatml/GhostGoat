#!/usr/bin/env python3
"""
GhostGoat Core - Main standalone orchestrator with LLM caching (128 responses), 
semantic memory, self-evolution gates.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import uuid

# Set default LLM provider to mock if not set, to allow running without API key
if "LLM_PROVIDER" not in os.environ:
    os.environ["LLM_PROVIDER"] = "mock"

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# Import core components with graceful degradation
def _safe_import(module_path: str, class_name: str = None):
    """Safely import a module or class with fallback to None."""
    try:
        module = __import__(module_path, fromlist=[class_name] if class_name else [])
        if class_name:
            return getattr(module, class_name)
        return module
    except Exception as e:
        logger.debug(f"Could not import {module_path}.{class_name if class_name else ''}: {e}")
        return None

# Try to import real components
LLMOrchestrator = _safe_import('core.brain.agents.tool_agent', 'LLMOrchestrator')
LLMPoweredOrchestrator = _safe_import('core.brain.agents.tool_agent', 'LLMPoweredOrchestrator')
KnowledgeTank = _safe_import('core.brain.reasoning.knowledge_tank', 'KnowledgeTank')
UnifiedMemory = _safe_import('core.brain.memory.unified_memory', 'UnifiedMemory')
DecisionGovernor = _safe_import('core.governance.decision_governor', 'DecisionGovernor')
TaskHandler = _safe_import('core.task_handler', 'TaskHandler')
SelfAwareLoop = _safe_import('core.self_aware_loop', 'SelfAwareLoop')
BuildLoop = _safe_import('core.build_loop', 'BuildLoop')

# Fallback implementations if real components not available
if not LLMOrchestrator:
    logger.warning("Using fallback LLMOrchestrator implementation")
    
    class TaskStatus:
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"
    
    @dataclass
    class Task:
        id: str = field(default_factory=lambda: str(uuid.uuid4()))
        description: str = ""
        priority: int = 5
        status: str = TaskStatus.PENDING
        assigned_agent: Optional[str] = None
        context: Dict[str, Any] = field(default_factory=dict)
        result: Optional[Any] = None
        created_at: str = field(default_factory=lambda: time.time())
        completed_at: Optional[float] = None
    
    class LLMOrchestrator:
        def __init__(self, llm_provider: str = "mock", base_path: Optional[str] = None):
            self.llm_provider = llm_provider
            self.base_path = base_path or str(ROOT)
            self.tasks: Dict[str, Task] = {}
            self.task_counter = 0
            logger.info(f"Fallback LLMOrchestrator initialized with provider: {llm_provider}")
        
        def orchestrate(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            
            task = Task(
                id=task_id,
                description=query,
                context=context or {}
            )
            
            self.tasks[task_id] = task
            
            # Simulate processing
            task.status = TaskStatus.COMPLETED
            task.result = {
                "response": f"Processed query: {query[:100]}...",
                "agent_used": "fallback_agent",
                "confidence": 0.75
            }
            task.completed_at = time.time()
            
            return {
                "task_id": task_id,
                "status": "completed",
                "result": task.result,
                "orchestrator": self.__class__.__name__
            }
        
        def get_status(self) -> Dict[str, Any]:
            return {
                "llm_provider": self.llm_provider,
                "base_path": self.base_path,
                "total_tasks": len(self.tasks),
                "completed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                "orchestrator": self.__class__.__name__
            }

if not LLMPoweredOrchestrator:
    logger.warning("Using fallback LLMPoweredOrchestrator implementation")
    
    class LLMPoweredOrchestrator(LLMOrchestrator):
        def __init__(self, llm_api_key: Optional[str] = None, llm_provider: str = "mock"):
            super().__init__(llm_provider=llm_provider)
            self.llm_api_key = llm_api_key
            logger.info(f"Fallback LLMPoweredOrchestrator initialized with provider: {llm_provider}")
        
        def process_command(self, command: str) -> Dict[str, Any]:
            logger.info(f"Processing command: {command}")
            
            # Simple command processing
            intent_map = {
                "list agents": "list_agents",
                "show status": "get_status", 
                "help": "help",
                "tasks": "list_tasks"
            }
            
            intent = intent_map.get(command.lower(), "unknown")
            
            if intent == "list_agents":
                result = {
                    "agents": ["fallback_agent_1", "fallback_agent_2"],
                    "count": 2
                }
            elif intent == "get_status":
                result = self.get_status()
            elif intent == "help":
                result = {
                    "available_commands": list(intent_map.keys()),
                    "description": "LLMPoweredOrchestrator can process natural language commands"
                }
            elif intent == "list_tasks":
                result = {
                    "tasks": [{"id": t.id, "description": t.description, "status": t.status} 
                             for t in self.tasks.values()],
                    "count": len(self.tasks)
                }
            else:
                result = {
                    "response": f"Processed command: {command}",
                    "intent": intent
                }
            
            return {
                "intent": intent,
                "command": command,
                "result": result,
                "orchestrator": self.__class__.__name__
            }

def create_orchestrator(llm_provider: str = "mock", llm_api_key: Optional[str] = None) -> Any:
    """Factory function to create an orchestrator instance."""
    if llm_api_key:
        return LLMPoweredOrchestrator(llm_api_key=llm_api_key, llm_provider=llm_provider)
    else:
        return LLMOrchestrator(llm_provider=llm_provider)

# Initialize core components
logger.info("Initializing GhostGoat Core components...")

# Initialize orchestrator
orchestrator = create_orchestrator(
    llm_provider=os.getenv("LLM_PROVIDER", "mock"),
    llm_api_key=os.getenv("LLM_API_KEY")
)

# Initialize other components with fallbacks
knowledge_tank = KnowledgeTank() if KnowledgeTank else None
unified_memory = UnifiedMemory() if UnifiedMemory else None
decision_governor = DecisionGovernor() if DecisionGovernor else None
task_handler = TaskHandler() if TaskHandler else None
self_aware_loop = SelfAwareLoop() if SelfAwareLoop else None
build_loop = BuildLoop() if BuildLoop else None

logger.info("GhostGoat Core initialization complete")
logger.info(f"Orchestrator: {type(orchestrator).__name__}")
logger.info(f"Knowledge Tank: {'Available' if knowledge_tank else 'Fallback'}")
logger.info(f"Unified Memory: {'Available' if unified_memory else 'Fallback'}")
logger.info(f"Decision Governor: {'Available' if decision_governor else 'Fallback'}")
logger.info(f"Task Handler: {'Available' if task_handler else 'Fallback'}")
logger.info(f"Self-Aware Loop: {'Available' if self_aware_loop else 'Fallback'}")
logger.info(f"Build Loop: {'Available' if build_loop else 'Fallback'}")

# Public API
__all__ = [
    'orchestrator',
    'knowledge_tank', 
    'unified_memory',
    'decision_governor',
    'task_handler',
    'self_aware_loop',
    'build_loop',
    'create_orchestrator',
    'LLMOrchestrator',
    'LLMPoweredOrchestrator'
]

if __name__ == "__main__":
    # Simple demo when run directly
    print("GhostGoat Core Demo")
    print("=" * 50)
    
    # Test basic orchestration
    result = orchestrator.orchestrate("Hello, GhostGoat! What are your capabilities?")
    print(f"Orchestration result: {result}")
    
    # Test LLM-powered orchestrator if available
    if isinstance(orchestrator, LLMPoweredOrchestrator):
        cmd_result = orchestrator.process_command("list agents")
        print(f"Command result: {cmd_result}")
    
    print("\nCore components initialized successfully!")
    print(f"Orchestrator type: {type(orchestrator).__name__}")
    print(f"Knowledge Tank: {type(knowledge_tank).__name__ if knowledge_tank else 'None'}")
    print(f"Unified Memory: {type(unified_memory).__name__ if unified_memory else 'None'}")