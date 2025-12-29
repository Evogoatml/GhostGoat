"""
GhostGoat LLM Orchestrator Integration Layer
Bridges orchestrator with existing GhostGoat components
"""

from typing import Dict, List, Optional, Any
from llm_orchestrator import LLMOrchestrator, Task, AgentCapability
from brain.core import Brain
from smart_moe import SmartMoE
from knowledge_tank import KnowledgeTank
import logging

logger = logging.getLogger(__name__)


class IntegratedOrchestrator(LLMOrchestrator):
    """
    Enhanced orchestrator with deep integration to GhostGoat components
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize SmartMoE for algorithm execution (optional)
        try:
            from smart_moe import SmartMoE
            self.smart_moe = SmartMoE(base_path=self.base_path)
            self.smart_moe.initialize_experts()
            logger.info("SmartMoE integrated")
        except Exception as e:
            logger.warning(f"SmartMoE initialization failed (optional): {e}")
            self.smart_moe = None
    
    async def _execute_task(self, task: Task, agent_name: str, algorithms: List[Dict]) -> Dict:
        """Enhanced task execution with SmartMoE integration"""
        logger.info(f"Executing task {task.id} on agent {agent_name}")
        
        try:
            # Try SmartMoE first for natural language execution
            if self.smart_moe:
                try:
                    result = self.smart_moe.run_natural_task(
                        task.description,
                        params=task.parameters
                    )
                    
                    if result.get('success'):
                        return {
                            "task_id": task.id,
                            "agent": agent_name,
                            "method": "smart_moe",
                            "algorithm": result.get('algorithm_used', {}).get('name', 'unknown'),
                            "success": True,
                            "output": result.get('output', ''),
                            "result": result
                        }
                except Exception as e:
                    logger.warning(f"SmartMoE execution failed: {e}, falling back to standard execution")
            
            # Fallback to parent implementation
            return await super()._execute_task(task, agent_name, algorithms)
        
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}")
            return {
                "task_id": task.id,
                "agent": agent_name,
                "success": False,
                "error": str(e)
            }
    
    def _find_algorithms(self, understanding: Dict) -> List[Dict]:
        """Enhanced algorithm finding with SmartMoE suggestions"""
        # Get base results from parent
        algorithms = super()._find_algorithms(understanding)
        
        # If SmartMoE available, get suggestions
        if self.smart_moe:
            try:
                intent = understanding.get("intent", "")
                suggestions = self.smart_moe.suggest_algorithms(intent, limit=5)
                
                # Merge suggestions with existing results
                seen_paths = {a.get('path') for a in algorithms}
                for suggestion in suggestions:
                    if suggestion.get('path') not in seen_paths:
                        algorithms.append(suggestion)
                        seen_paths.add(suggestion['path'])
            except Exception as e:
                logger.warning(f"Error getting SmartMoE suggestions: {e}")
        
        return algorithms
    
    async def orchestrate_with_brain(self, user_query: str, user_id: int = 0) -> Dict[str, Any]:
        """
        Orchestrate with Brain integration - uses Brain's reasoning capabilities
        """
        # First, let Brain interpret the command
        brain_plan = self.brain.handle(user_id, user_query)
        
        # Then orchestrate with Brain's understanding as context
        context = {
            "brain_interpretation": brain_plan,
            "user_id": user_id
        }
        
        return await self.orchestrate(user_query, context)
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrated components"""
        status = self.get_status()
        
        integrations = {
            "brain": self.brain is not None,
            "knowledge_tank": self.knowledge_tank is not None,
            "semantic_tank": self.semantic_tank is not None,
            "smart_moe": self.smart_moe is not None,
            "agent_network": self.agent_network is not None
        }
        
        # Get component-specific stats
        if self.knowledge_tank:
            try:
                tank_stats = self.knowledge_tank.get_stats()
                integrations["knowledge_tank_stats"] = tank_stats
            except:
                pass
        
        if self.agent_network:
            integrations["agent_network_agents"] = len(self.agent_network.agents)
            integrations["agent_network_connections"] = len(self.agent_network.connections)
        
        status["integrations"] = integrations
        return status


class OrchestratorBridge:
    """
    Bridge class for backward compatibility with existing GhostGoat interfaces
    """
    
    def __init__(self, orchestrator: IntegratedOrchestrator):
        self.orchestrator = orchestrator
    
    def handle(self, user_id: int, user_input: str) -> str:
        """Compatible with Brain.handle interface"""
        import asyncio
        
        result = asyncio.run(
            self.orchestrator.orchestrate_with_brain(user_input, user_id)
        )
        
        # Return formatted result
        final_result = result.get("final_result", {})
        return final_result.get("summary", str(result))
    
    def search_algorithms(self, query: str, limit: int = 10) -> List[Dict]:
        """Compatible with KnowledgeTank.search interface"""
        return self.orchestrator.knowledge_tank.search(query, limit=limit)
    
    def execute_natural_task(self, query: str) -> Dict:
        """Compatible with SmartMoE.run_natural_task interface"""
        import asyncio
        
        result = asyncio.run(self.orchestrator.orchestrate(query))
        return result


# Factory function for easy initialization
def create_orchestrator(
    llm_provider: str = "mock",
    llm_model: str = "gpt-4",
    llm_api_key: Optional[str] = None,
    use_integration: bool = True
) -> IntegratedOrchestrator:
    """
    Create and initialize an integrated orchestrator
    
    Args:
        llm_provider: LLM provider ("openai", "anthropic", "mock")
        llm_model: Model name
        llm_api_key: API key (or use env vars)
        use_integration: Whether to use integrated components
    
    Returns:
        Configured IntegratedOrchestrator instance
    """
    if use_integration:
        return IntegratedOrchestrator(
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_api_key=llm_api_key
        )
    else:
        return LLMOrchestrator(
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_api_key=llm_api_key
        )
