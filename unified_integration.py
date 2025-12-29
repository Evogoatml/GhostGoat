"""
Unified Integration Layer for GhostGoat Ecosystem
Connects all agent systems through a common interface
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from unified_config import UnifiedConfig, get_config

logger = logging.getLogger(__name__)


class SystemType(Enum):
    """System types"""
    GHOSTGOAT_AGENT = "ghostgoat_agent"
    NEXUSEVO = "nexusevo"
    AUTONOMOUS_AGENT = "autonomous_agent"
    ORCHESTRATOR = "orchestrator"
    ADAP_ENGINE = "adap_engine"


@dataclass
class Task:
    """Unified task representation"""
    id: str
    description: str
    system: SystemType
    priority: int = 5
    parameters: Dict[str, Any] = None
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SystemAdapter:
    """Base class for system adapters"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.system = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the system"""
        raise NotImplementedError
    
    async def execute(self, task: Task) -> TaskResult:
        """Execute a task"""
        raise NotImplementedError
    
    async def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        raise NotImplementedError
    
    async def shutdown(self):
        """Shutdown the system"""
        pass


class GhostGoatAgentAdapter(SystemAdapter):
    """Adapter for GhostGoat Agent"""
    
    async def initialize(self) -> bool:
        try:
            import sys
            sys.path.insert(0, self.config.agents_path + "/ghostgoat_agent")
            from core.ghostgoat import GhostGoatAgent
            
            self.system = GhostGoatAgent()
            await self.system.start()
            self.initialized = True
            logger.info("GhostGoat Agent adapter initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GhostGoat Agent: {e}")
            return False
    
    async def execute(self, task: Task) -> TaskResult:
        if not self.initialized:
            await self.initialize()
        
        start_time = datetime.now()
        try:
            # Convert task to GhostGoat Agent format
            result = await self.system.run_control_loop()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=True,
                output=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time
            )
    
    async def get_status(self) -> Dict[str, Any]:
        if not self.system:
            return {"status": "not_initialized"}
        
        return {
            "status": "running" if self.system.running else "idle",
            "goals": len(self.system.run_context.get("goals", [])),
            "execution_history": len(self.system.run_context.get("execution_history", []))
        }


class NexusEvoAdapter(SystemAdapter):
    """Adapter for NexusEvo"""
    
    async def initialize(self) -> bool:
        try:
            import sys
            sys.path.insert(0, self.config.agents_path + "/nexusevo")
            from agents.orchestrator import OrchestratorAgent
            
            self.system = OrchestratorAgent()
            self.initialized = True
            logger.info("NexusEvo adapter initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize NexusEvo: {e}")
            return False
    
    async def execute(self, task: Task) -> TaskResult:
        if not self.initialized:
            await self.initialize()
        
        start_time = datetime.now()
        try:
            result = self.system.execute(task.description, task.parameters)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=True,
                output=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time
            )
    
    async def get_status(self) -> Dict[str, Any]:
        if not self.system:
            return {"status": "not_initialized"}
        
        status = self.system.get_status()
        return {
            "status": status.get("state", {}).get("status", "unknown"),
            "tasks_completed": len(self.system.task_history)
        }


class AutonomousAgentAdapter(SystemAdapter):
    """Adapter for Autonomous Agent"""
    
    async def initialize(self) -> bool:
        try:
            import sys
            sys.path.insert(0, self.config.bots_path + "/autonomous_agent")
            from core.agent import AutonomousAgent
            
            self.system = AutonomousAgent()
            self.initialized = True
            logger.info("Autonomous Agent adapter initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Autonomous Agent: {e}")
            return False
    
    async def execute(self, task: Task) -> TaskResult:
        if not self.initialized:
            await self.initialize()
        
        start_time = datetime.now()
        try:
            # Autonomous Agent expects a goal, not a task
            await self.system.execute_goal(task.description)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=True,
                output="Goal executed",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time
            )
    
    async def get_status(self) -> Dict[str, Any]:
        if not self.system:
            return {"status": "not_initialized"}
        
        return {
            "status": "running" if self.system.running else "idle",
            "current_goal": self.system.current_goal
        }


class OrchestratorAdapter(SystemAdapter):
    """Adapter for GhostGoat Orchestrator"""
    
    async def initialize(self) -> bool:
        try:
            from llm_orchestrator import LLMOrchestrator
            
            self.system = LLMOrchestrator(
                llm_provider=self.config.llm.provider.value,
                llm_model=self.config.llm.model,
                llm_api_key=self.config.llm.api_key,
                base_path=self.config.base_path
            )
            self.initialized = True
            logger.info("Orchestrator adapter initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Orchestrator: {e}")
            return False
    
    async def execute(self, task: Task) -> TaskResult:
        if not self.initialized:
            await self.initialize()
        
        start_time = datetime.now()
        try:
            result = await self.system.orchestrate(task.description, task.parameters)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task.id,
                success=result.get("final_result", {}).get("success", True),
                output=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time
            )
    
    async def get_status(self) -> Dict[str, Any]:
        if not self.system:
            return {"status": "not_initialized"}
        
        return self.system.get_status()


class UnifiedIntegrationLayer:
    """
    Unified integration layer for all systems
    Provides a common interface to interact with all agent systems
    """
    
    def __init__(self, config: Optional[UnifiedConfig] = None):
        self.config = config or get_config()
        self.adapters: Dict[SystemType, SystemAdapter] = {}
        self.task_history: List[TaskResult] = []
    
    async def initialize(self, systems: Optional[List[SystemType]] = None):
        """Initialize specified systems or all systems"""
        if systems is None:
            systems = list(SystemType)
        
        adapter_classes = {
            SystemType.GHOSTGOAT_AGENT: GhostGoatAgentAdapter,
            SystemType.NEXUSEVO: NexusEvoAdapter,
            SystemType.AUTONOMOUS_AGENT: AutonomousAgentAdapter,
            SystemType.ORCHESTRATOR: OrchestratorAdapter,
        }
        
        for system_type in systems:
            if system_type in adapter_classes:
                adapter = adapter_classes[system_type](self.config)
                success = await adapter.initialize()
                if success:
                    self.adapters[system_type] = adapter
                    logger.info(f"Initialized {system_type.value}")
                else:
                    logger.warning(f"Failed to initialize {system_type.value}")
    
    async def execute_task(
        self,
        description: str,
        system: SystemType,
        priority: int = 5,
        parameters: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Execute a task on a specific system"""
        if system not in self.adapters:
            return TaskResult(
                task_id="",
                success=False,
                output=None,
                error=f"System {system.value} not initialized"
            )
        
        task = Task(
            id=f"task_{datetime.now().timestamp()}",
            description=description,
            system=system,
            priority=priority,
            parameters=parameters or {}
        )
        
        adapter = self.adapters[system]
        result = await adapter.execute(task)
        
        self.task_history.append(result)
        return result
    
    async def execute_with_routing(
        self,
        description: str,
        preferred_system: Optional[SystemType] = None
    ) -> TaskResult:
        """Execute task with automatic system routing"""
        # If preferred system specified, use it
        if preferred_system and preferred_system in self.adapters:
            return await self.execute_task(description, preferred_system)
        
        # Otherwise, use orchestrator to route
        if SystemType.ORCHESTRATOR in self.adapters:
            return await self.execute_task(description, SystemType.ORCHESTRATOR)
        
        # Fallback to first available system
        if self.adapters:
            first_system = list(self.adapters.keys())[0]
            return await self.execute_task(description, first_system)
        
        return TaskResult(
            task_id="",
            success=False,
            output=None,
            error="No systems available"
        )
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all systems"""
        status = {}
        for system_type, adapter in self.adapters.items():
            status[system_type.value] = await adapter.get_status()
        return status
    
    async def shutdown_all(self):
        """Shutdown all systems"""
        for adapter in self.adapters.values():
            await adapter.shutdown()
        self.adapters.clear()
    
    def get_task_history(self, limit: int = 100) -> List[TaskResult]:
        """Get task execution history"""
        return self.task_history[-limit:]


# Global instance
_integration_layer: Optional[UnifiedIntegrationLayer] = None


def get_integration_layer(config: Optional[UnifiedConfig] = None) -> UnifiedIntegrationLayer:
    """Get global integration layer instance"""
    global _integration_layer
    
    if _integration_layer is None:
        _integration_layer = UnifiedIntegrationLayer(config)
    
    return _integration_layer


async def init_integration(systems: Optional[List[SystemType]] = None) -> UnifiedIntegrationLayer:
    """Initialize integration layer"""
    layer = get_integration_layer()
    await layer.initialize(systems)
    return layer
