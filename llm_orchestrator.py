"""
GhostGoat LLM Orchestrator
Core Neural Language Model orchestrator for multi-agent system coordination

This module provides:
- LLM-based task decomposition and planning
- Intelligent agent selection and routing
- Multi-agent coordination and communication
- Integration with Brain, Knowledge Tank, and Agent Network
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import logging

# Core imports
from brain.core import Brain
from knowledge_tank import KnowledgeTank
from semantic_tank import SemanticKnowledgeTank
from agent_network import AgentNetwork

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentCapability(Enum):
    """Agent capability types"""
    CRYPTOGRAPHY = "cryptography"
    MACHINE_LEARNING = "machine_learning"
    GRAPH_ANALYSIS = "graphs"
    DATA_STRUCTURES = "data_structures"
    MATHEMATICS = "mathematics"
    NETWORKING = "network"
    GENERAL = "general"


@dataclass
class Task:
    """Represents a task to be executed"""
    id: str
    description: str
    priority: int = 5
    dependencies: List[str] = None
    required_capabilities: List[AgentCapability] = None
    parameters: Dict[str, Any] = None
    status: str = "pending"
    assigned_agent: Optional[str] = None
    result: Optional[Any] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.required_capabilities is None:
            self.required_capabilities = []
        if self.parameters is None:
            self.parameters = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class AgentProfile:
    """Profile of an agent in the network"""
    name: str
    host: str
    port: int
    capabilities: List[AgentCapability]
    status: str = "available"
    current_tasks: int = 0
    max_concurrent_tasks: int = 5
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {"success_rate": 1.0, "avg_time": 0.0}


class LLMOrchestrator:
    """
    Core LLM Orchestrator for GhostGoat multi-agent system
    
    Uses LLM APIs for:
    - Natural language understanding
    - Task decomposition
    - Agent selection
    - Plan generation
    - Coordination logic
    """
    
    def __init__(
        self,
        llm_provider: str = "openai",  # "openai", "anthropic", "local", "mock"
        llm_model: str = "gpt-4",
        llm_api_key: Optional[str] = None,
        base_path: str = "/home/chewlo/GhostGoat"
    ):
        self.base_path = base_path
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Initialize core components
        self.brain = Brain()
        self.knowledge_tank = KnowledgeTank()
        self.semantic_tank = SemanticKnowledgeTank() if self._check_semantic_available() else None
        self.agent_network = AgentNetwork()
        
        # Task management
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.execution_history: List[Dict] = []
        
        # Agent profiles
        self.agent_profiles: Dict[str, AgentProfile] = {}
        self._initialize_agent_profiles()
        
        # LLM client
        self.llm_client = self._initialize_llm_client()
        
        logger.info(f"LLM Orchestrator initialized with provider: {llm_provider}")
    
    def _check_semantic_available(self) -> bool:
        """Check if semantic search is available"""
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            return False
    
    def _initialize_llm_client(self):
        """Initialize LLM client based on provider"""
        if self.llm_provider == "openai":
            try:
                import openai
                if self.llm_api_key:
                    openai.api_key = self.llm_api_key
                return openai
            except ImportError:
                logger.warning("OpenAI library not installed. Using mock LLM.")
                return self._create_mock_llm()
        
        elif self.llm_provider == "anthropic":
            try:
                import anthropic
                if self.llm_api_key:
                    return anthropic.Anthropic(api_key=self.llm_api_key)
            except ImportError:
                logger.warning("Anthropic library not installed. Using mock LLM.")
                return self._create_mock_llm()
        
        elif self.llm_provider == "mock":
            return self._create_mock_llm()
        
        else:
            logger.warning(f"Unknown LLM provider: {self.llm_provider}. Using mock LLM.")
            return self._create_mock_llm()
    
    def _create_mock_llm(self):
        """Create a mock LLM for testing without API"""
        class MockLLM:
            def chat(self, messages, model=None, **kwargs):
                class Response:
                    def __init__(self):
                        self.choices = [type('obj', (object,), {
                            'message': type('obj', (object,), {
                                'content': self._generate_mock_response(messages)
                            })()
                        })()]
                    
                    def _generate_mock_response(self, messages):
                        """Generate a basic mock response"""
                        last_msg = messages[-1]["content"] if messages else ""
                        
                        # Simple pattern matching for mock responses
                        if "decompose" in last_msg.lower() or "break down" in last_msg.lower():
                            return json.dumps({
                                "tasks": [
                                    {"description": "Analyze input", "capability": "general"},
                                    {"description": "Process data", "capability": "general"},
                                    {"description": "Generate output", "capability": "general"}
                                ]
                            })
                        elif "select agent" in last_msg.lower() or "route" in last_msg.lower():
                            return json.dumps({
                                "selected_agent": "local_agent_1",
                                "reasoning": "Best match for task requirements"
                            })
                        else:
                            return json.dumps({"response": "Mock LLM response", "input": last_msg[:100]})
                
                return Response()
        
        return MockLLM()
    
    def _initialize_agent_profiles(self):
        """Initialize agent profiles from agent network"""
        # Map agent network agents to profiles
        for agent_name, config in self.agent_network.agents.items():
            # Infer capabilities from agent name/type
            capabilities = self._infer_capabilities(agent_name, config)
            
            self.agent_profiles[agent_name] = AgentProfile(
                name=agent_name,
                host=config['host'],
                port=config['port'],
                capabilities=capabilities,
                status="available"
            )
    
    def _infer_capabilities(self, agent_name: str, config: Dict) -> List[AgentCapability]:
        """Infer agent capabilities from name and config"""
        capabilities = []
        name_lower = agent_name.lower()
        
        if 'crypto' in name_lower:
            capabilities.append(AgentCapability.CRYPTOGRAPHY)
        if 'ml' in name_lower or 'machine' in name_lower:
            capabilities.append(AgentCapability.MACHINE_LEARNING)
        if 'graph' in name_lower:
            capabilities.append(AgentCapability.GRAPH_ANALYSIS)
        if 'math' in name_lower:
            capabilities.append(AgentCapability.MATHEMATICS)
        if 'network' in name_lower:
            capabilities.append(AgentCapability.NETWORKING)
        
        # Default to general if no specific capabilities found
        if not capabilities:
            capabilities.append(AgentCapability.GENERAL)
        
        return capabilities
    
    async def orchestrate(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main orchestration method - coordinates multi-agent execution
        
        Args:
            user_query: Natural language query from user
            context: Optional context information
            
        Returns:
            Execution result with task breakdown and outcomes
        """
        logger.info(f"Orchestrating query: {user_query}")
        
        # Step 1: Understand query using LLM
        understanding = await self._understand_query(user_query, context)
        
        # Step 2: Decompose into tasks using LLM
        tasks = await self._decompose_task(understanding)
        
        # Step 3: Find relevant algorithms from knowledge tank
        algorithms = self._find_algorithms(understanding)
        
        # Step 4: Select agents for each task using LLM
        agent_assignments = await self._select_agents(tasks, algorithms)
        
        # Step 5: Execute tasks in coordination
        results = await self._execute_coordinated(tasks, agent_assignments, algorithms)
        
        # Step 6: Synthesize results using LLM
        final_result = await self._synthesize_results(user_query, results, understanding)
        
        # Step 7: Learn and update
        self._update_learning(user_query, tasks, results, final_result)
        
        return {
            "query": user_query,
            "understanding": understanding,
            "tasks": [asdict(t) for t in tasks],
            "algorithms_used": algorithms,
            "agent_assignments": agent_assignments,
            "results": results,
            "final_result": final_result,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _understand_query(self, query: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Use LLM to understand the user query"""
        prompt = f"""
Analyze this user query and extract key information:

Query: {query}
Context: {json.dumps(context) if context else "None"}

Return JSON with:
- intent: Main goal/purpose
- domain: Primary domain (cryptography, ml, graphs, etc.)
- complexity: Simple/Medium/Complex
- required_capabilities: List of needed agent capabilities
- parameters: Any specific parameters mentioned
"""
        
        response = self._call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "intent": query,
                "domain": "general",
                "complexity": "medium",
                "required_capabilities": [],
                "parameters": {}
            }
    
    async def _decompose_task(self, understanding: Dict) -> List[Task]:
        """Use LLM to decompose task into subtasks"""
        prompt = f"""
Break down this task into executable subtasks:

Task Understanding:
{json.dumps(understanding, indent=2)}

Return JSON array of tasks, each with:
- description: Clear task description
- priority: 1-10 (10 highest)
- required_capabilities: List of needed capabilities
- dependencies: List of task IDs this depends on (use indices)
"""
        
        response = self._call_llm(prompt)
        try:
            task_data = json.loads(response)
            tasks = []
            
            for i, task_info in enumerate(task_data.get("tasks", [])):
                task = Task(
                    id=f"task_{i}_{datetime.now().timestamp()}",
                    description=task_info.get("description", ""),
                    priority=task_info.get("priority", 5),
                    required_capabilities=[
                        AgentCapability(c) for c in task_info.get("required_capabilities", [])
                        if c in [cap.value for cap in AgentCapability]
                    ],
                    dependencies=task_info.get("dependencies", []),
                    parameters=task_info.get("parameters", {})
                )
                tasks.append(task)
                self.tasks[task.id] = task
            
            return tasks
        except Exception as e:
            logger.error(f"Error decomposing task: {e}")
            # Fallback: create single task
            task = Task(
                id=f"task_0_{datetime.now().timestamp()}",
                description=understanding.get("intent", "Execute task"),
                required_capabilities=[
                    AgentCapability(c) for c in understanding.get("required_capabilities", [])
                    if c in [cap.value for cap in AgentCapability]
                ]
            )
            self.tasks[task.id] = task
            return [task]
    
    def _find_algorithms(self, understanding: Dict) -> List[Dict]:
        """Find relevant algorithms from knowledge tank"""
        domain = understanding.get("domain", "general")
        intent = understanding.get("intent", "")
        
        # Search knowledge tank
        results = self.knowledge_tank.search(intent, category=domain, limit=5)
        
        # If semantic tank available, use it for better results
        if self.semantic_tank:
            semantic_results = self.semantic_tank.semantic_search(intent, top_k=5)
            # Merge and deduplicate
            seen_paths = {r['path'] for r in results}
            for r in semantic_results:
                if r['path'] not in seen_paths:
                    results.append(r)
                    seen_paths.add(r['path'])
        
        return results[:10]  # Limit to top 10
    
    async def _select_agents(self, tasks: List[Task], algorithms: List[Dict]) -> Dict[str, str]:
        """Use LLM to select best agents for each task"""
        agent_assignments = {}
        
        for task in tasks:
            prompt = f"""
Select the best agent for this task:

Task: {task.description}
Required Capabilities: {[c.value for c in task.required_capabilities]}
Available Agents: {json.dumps({name: [c.value for c in profile.capabilities] 
                                for name, profile in self.agent_profiles.items()}, indent=2)}

Return JSON with:
- selected_agent: Agent name
- reasoning: Why this agent was selected
"""
            
            response = self._call_llm(prompt)
            try:
                selection = json.loads(response)
                agent_name = selection.get("selected_agent")
                
                # Validate agent exists
                if agent_name in self.agent_profiles:
                    agent_assignments[task.id] = agent_name
                    task.assigned_agent = agent_name
                else:
                    # Fallback: select first available agent
                    available = [name for name, profile in self.agent_profiles.items() 
                               if profile.status == "available"]
                    if available:
                        agent_assignments[task.id] = available[0]
                        task.assigned_agent = available[0]
            except Exception as e:
                logger.error(f"Error selecting agent for task {task.id}: {e}")
                # Fallback: round-robin assignment
                agents = list(self.agent_profiles.keys())
                if agents:
                    agent_assignments[task.id] = agents[len(agent_assignments) % len(agents)]
        
        return agent_assignments
    
    async def _execute_coordinated(
        self, 
        tasks: List[Task], 
        agent_assignments: Dict[str, str],
        algorithms: List[Dict]
    ) -> List[Dict]:
        """Execute tasks in coordinated manner respecting dependencies"""
        results = []
        completed_tasks = set()
        
        # Sort tasks by priority and dependencies
        sorted_tasks = self._topological_sort(tasks)
        
        for task in sorted_tasks:
            # Wait for dependencies
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in completed_tasks:
                        logger.info(f"Waiting for dependency {dep_id} to complete")
                        # In real implementation, wait for dependency completion
            
            # Execute task
            agent_name = agent_assignments.get(task.id)
            if not agent_name:
                results.append({
                    "task_id": task.id,
                    "status": "failed",
                    "error": "No agent assigned"
                })
                continue
            
            task.status = "executing"
            result = await self._execute_task(task, agent_name, algorithms)
            task.status = "completed" if result.get("success") else "failed"
            task.result = result
            results.append(result)
            completed_tasks.add(task.id)
        
        return results
    
    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks respecting dependencies"""
        # Simple implementation - in production, use proper topological sort
        # For now, just sort by priority
        return sorted(tasks, key=lambda t: t.priority, reverse=True)
    
    async def _execute_task(self, task: Task, agent_name: str, algorithms: List[Dict]) -> Dict:
        """Execute a single task on assigned agent"""
        logger.info(f"Executing task {task.id} on agent {agent_name}")
        
        try:
            # Find matching algorithm
            algorithm = self._match_algorithm_to_task(task, algorithms)
            
            if algorithm:
                # Use agent network to execute
                if agent_name in self.agent_network.connections:
                    # Execute via SSH
                    command = f"python {self.base_path}/algorithms/{algorithm['path']}"
                    result = self.agent_network.execute(agent_name, command)
                    
                    return {
                        "task_id": task.id,
                        "agent": agent_name,
                        "algorithm": algorithm['name'],
                        "success": result['exit_code'] == 0,
                        "output": result['stdout'],
                        "error": result['stderr'] if result['exit_code'] != 0 else None
                    }
                else:
                    # Use Brain to execute locally
                    result = self.brain.handle(
                        user_id=hash(agent_name) % 10000,
                        user_input=task.description
                    )
                    
                    return {
                        "task_id": task.id,
                        "agent": "local_brain",
                        "algorithm": algorithm.get('name', 'unknown'),
                        "success": True,
                        "output": result
                    }
            else:
                # No algorithm found, use Brain's general handling
                result = self.brain.handle(
                    user_id=hash(agent_name) % 10000,
                    user_input=task.description
                )
                
                return {
                    "task_id": task.id,
                    "agent": "local_brain",
                    "success": True,
                    "output": result
                }
        
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}")
            return {
                "task_id": task.id,
                "agent": agent_name,
                "success": False,
                "error": str(e)
            }
    
    def _match_algorithm_to_task(self, task: Task, algorithms: List[Dict]) -> Optional[Dict]:
        """Match best algorithm to task"""
        if not algorithms:
            return None
        
        # Simple matching - in production, use more sophisticated matching
        task_desc_lower = task.description.lower()
        
        for algo in algorithms:
            algo_desc = algo.get('description', '').lower()
            algo_name = algo.get('name', '').lower()
            
            # Check if task keywords match algorithm
            task_words = set(task_desc_lower.split())
            algo_words = set((algo_desc + ' ' + algo_name).split())
            
            if task_words.intersection(algo_words):
                return algo
        
        return algorithms[0] if algorithms else None
    
    async def _synthesize_results(
        self, 
        original_query: str, 
        results: List[Dict],
        understanding: Dict
    ) -> Dict[str, Any]:
        """Use LLM to synthesize final result from task results"""
        prompt = f"""
Synthesize a coherent response from these task execution results:

Original Query: {original_query}
Task Understanding: {json.dumps(understanding, indent=2)}

Execution Results:
{json.dumps(results, indent=2)}

Return JSON with:
- summary: Brief summary of what was accomplished
- key_findings: List of key findings
- recommendations: Any recommendations
- success: Overall success status
"""
        
        response = self._call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "summary": "Tasks executed",
                "key_findings": [],
                "recommendations": [],
                "success": all(r.get("success", False) for r in results)
            }
    
    def _update_learning(
        self, 
        query: str, 
        tasks: List[Task], 
        results: List[Dict],
        final_result: Dict
    ):
        """Update learning systems with execution results"""
        # Store in execution history
        self.execution_history.append({
            "query": query,
            "tasks": [asdict(t) for t in tasks],
            "results": results,
            "final_result": final_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update agent performance metrics
        for result in results:
            agent_name = result.get("agent")
            if agent_name in self.agent_profiles:
                profile = self.agent_profiles[agent_name]
                # Update success rate
                current_rate = profile.performance_metrics.get("success_rate", 1.0)
                success = result.get("success", False)
                # Simple moving average
                profile.performance_metrics["success_rate"] = (current_rate * 0.9) + (1.0 if success else 0.0) * 0.1
    
    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call LLM API with prompt"""
        try:
            if self.llm_provider == "openai" and hasattr(self.llm_client, 'ChatCompletion'):
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.llm_client.ChatCompletion.create(
                    model=self.llm_model,
                    messages=messages,
                    temperature=0.7
                )
                return response.choices[0].message.content
            
            elif self.llm_provider == "anthropic":
                messages = []
                if system_prompt:
                    messages.append({"role": "user", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.llm_client.messages.create(
                    model=self.llm_model,
                    max_tokens=1024,
                    messages=messages
                )
                return response.content[0].text
            
            elif hasattr(self.llm_client, 'chat'):
                # Mock or custom LLM
                messages = [{"role": "user", "content": prompt}]
                if system_prompt:
                    messages.insert(0, {"role": "system", "content": system_prompt})
                
                response = self.llm_client.chat(messages=messages)
                if hasattr(response, 'choices'):
                    return response.choices[0].message.content
                return str(response)
            
            else:
                # Fallback
                return json.dumps({"error": "LLM not properly configured"})
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return json.dumps({"error": str(e)})
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == "pending"]),
            "active_agents": len([a for a in self.agent_profiles.values() if a.status == "available"]),
            "execution_history_count": len(self.execution_history),
            "knowledge_tank_size": self.knowledge_tank.get_stats().get("total_algorithms", 0)
        }


# Convenience function for easy usage
async def orchestrate_query(query: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to orchestrate a query"""
    orchestrator = LLMOrchestrator(**kwargs)
    return await orchestrator.orchestrate(query)


if __name__ == "__main__":
    # Example usage
    async def main():
        orchestrator = LLMOrchestrator(llm_provider="mock")  # Use mock for testing
        
        result = await orchestrator.orchestrate(
            "Encrypt a message using RSA and then hash it with SHA256"
        )
        
        print("\n=== Orchestration Result ===")
        print(json.dumps(result, indent=2))
        
        print("\n=== Orchestrator Status ===")
        print(json.dumps(orchestrator.get_status(), indent=2))
    
    asyncio.run(main())
