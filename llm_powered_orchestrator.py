#!/usr/bin/env python3
"""
LLM-POWERED AI ORCHESTRATOR
Natural language control of multi-agent system
The LLM understands intent and controls the orchestrator
Integrated with GhostGoat LLM Orchestrator
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

# Import GhostGoat orchestrator
from llm_orchestrator import LLMOrchestrator, Task, AgentCapability
from orchestrator_integration import IntegratedOrchestrator

# Import config system
try:
    from config_system import EnvLoader, ConfigManager, ProfessionalLogger
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    print("⚠️  Running without config system")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# ENUMS AND DATA CLASSES
# ============================================

class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class AgentType(Enum):
    WORKER = "worker"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    MONITOR = "monitor"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Agent:
    """Agent representation"""
    agent_id: str
    name: str
    agent_type: AgentType
    capabilities: List[str]
    status: AgentStatus = AgentStatus.IDLE
    tasks_completed: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Task:
    """Task representation"""
    task_id: str
    name: str
    function: str
    task_params: Dict[str, Any]
    priority: str = "normal"
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    result: Any = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Workflow:
    """Workflow representation"""
    workflow_id: str
    name: str
    tasks: List[str]  # Task IDs
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================
# LLM INTERFACE
# ============================================

class LLMInterface:
    """Interface to communicate with Language Models"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo", provider: str = "openai"):
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.conversation_history = []
        
        # Fallback to pattern matching if no API key
        self.use_patterns = not api_key
        
        # Initialize LLM client if available
        self.llm_client = None
        if api_key and provider == "openai":
            try:
                import openai
                openai.api_key = api_key
                self.llm_client = openai
                self.use_patterns = False
            except ImportError:
                logger.warning("OpenAI library not installed, using pattern matching")
    
    async def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process natural language input and extract intent
        Returns: {
            'intent': 'create_agent' | 'add_task' | 'execute' | 'status',
            'params': {...}
        }
        """
        if self.use_patterns:
            return self._pattern_based_processing(user_input)
        else:
            return await self._llm_processing(user_input)
    
    def _pattern_based_processing(self, user_input: str) -> Dict[str, Any]:
        """Pattern-based intent extraction (fallback without API)"""
        user_input_lower = user_input.lower()
        
        # Create Agent patterns
        if any(word in user_input_lower for word in ['create agent', 'new agent', 'spawn agent', 'make agent']):
            return self._extract_create_agent(user_input)
        
        # Add Task patterns
        elif any(word in user_input_lower for word in ['add task', 'create task', 'new task', 'run task', 'execute task']):
            return self._extract_add_task(user_input)
        
        # Create Workflow patterns
        elif any(word in user_input_lower for word in ['create workflow', 'new workflow', 'workflow']):
            return self._extract_create_workflow(user_input)
        
        # Teach Agent patterns
        elif any(word in user_input_lower for word in ['teach', 'train', 'learn', 'add skill']):
            return self._extract_teach_agent(user_input)
        
        # Status patterns
        elif any(word in user_input_lower for word in ['status', 'show agents', 'list agents', 'what agents']):
            return {'intent': 'list_agents', 'params': {}}
        
        elif any(word in user_input_lower for word in ['show tasks', 'list tasks', 'task status']):
            return {'intent': 'list_tasks', 'params': {}}
        
        elif any(word in user_input_lower for word in ['stats', 'statistics', 'metrics']):
            return {'intent': 'show_stats', 'params': {}}
        
        # Execute patterns
        elif any(word in user_input_lower for word in ['execute', 'run', 'start', 'process']):
            return {'intent': 'execute', 'params': {}}
        
        # Help patterns
        elif any(word in user_input_lower for word in ['help', 'what can you do', 'commands']):
            return {'intent': 'help', 'params': {}}
        
        else:
            return {
                'intent': 'unknown',
                'params': {'original': user_input}
            }
    
    def _extract_create_agent(self, text: str) -> Dict[str, Any]:
        """Extract agent creation parameters"""
        # Extract name
        name_match = re.search(r'(?:named?|called)\s+["\']?(\w+)["\']?', text, re.IGNORECASE)
        name = name_match.group(1) if name_match else f"Agent_{int(time.time())}"
        
        # Extract type
        agent_type = 'worker'
        if 'specialist' in text.lower():
            agent_type = 'specialist'
        elif 'coordinator' in text.lower():
            agent_type = 'coordinator'
        elif 'monitor' in text.lower():
            agent_type = 'monitor'
        
        # Extract capabilities
        capabilities = []
        if 'calculate' in text.lower() or 'math' in text.lower():
            capabilities.append('calculate')
        if 'analyze' in text.lower() or 'data' in text.lower():
            capabilities.append('analyze')
        if 'process' in text.lower() or 'text' in text.lower():
            capabilities.append('process_text')
        if 'crypto' in text.lower() or 'encrypt' in text.lower():
            capabilities.append('cryptography')
        if 'graph' in text.lower():
            capabilities.append('graph_analysis')
        if 'ml' in text.lower() or 'machine learning' in text.lower():
            capabilities.append('machine_learning')
        
        return {
            'intent': 'create_agent',
            'params': {
                'name': name,
                'type': agent_type,
                'capabilities': capabilities or ['general']
            }
        }
    
    def _extract_add_task(self, text: str) -> Dict[str, Any]:
        """Extract task parameters"""
        # Extract task name/description
        name_match = re.search(r'task\s+["\']?([^"\']+)["\']?', text, re.IGNORECASE)
        if not name_match:
            name_match = re.search(r'(?:execute|run|do)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else text.strip()
        
        # Extract function
        function = 'general'
        if 'calculate' in text.lower() or 'compute' in text.lower():
            function = 'calculate'
            # Extract expression
            expr_match = re.search(r'(?:calculate|compute)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
            if expr_match:
                params = {'expression': expr_match.group(1).strip()}
            else:
                params = {}
        elif 'analyze' in text.lower():
            function = 'analyze'
            params = {}
        elif 'process' in text.lower():
            function = 'process_text'
            params = {}
        elif 'encrypt' in text.lower() or 'crypto' in text.lower():
            function = 'cryptography'
            params = {}
        elif 'graph' in text.lower():
            function = 'graph_analysis'
            params = {}
        elif 'ml' in text.lower() or 'train' in text.lower():
            function = 'machine_learning'
            params = {}
        else:
            params = {}
        
        # Extract priority
        priority = 'normal'
        if 'high priority' in text.lower() or 'urgent' in text.lower() or 'critical' in text.lower():
            priority = 'high'
        elif 'low priority' in text.lower():
            priority = 'low'
        
        return {
            'intent': 'add_task',
            'params': {
                'name': name,
                'function': function,
                'task_params': params,
                'priority': priority
            }
        }
    
    def _extract_create_workflow(self, text: str) -> Dict[str, Any]:
        """Extract workflow parameters"""
        name_match = re.search(r'workflow\s+["\']?(\w+)["\']?', text, re.IGNORECASE)
        workflow_name = name_match.group(1) if name_match else f"Workflow_{int(time.time())}"
        
        return {
            'intent': 'create_workflow',
            'params': {
                'workflow_id': workflow_name,
                'tasks': []  # Would need more parsing for task list
            }
        }
    
    def _extract_teach_agent(self, text: str) -> Dict[str, Any]:
        """Extract teaching parameters"""
        # Extract agent name
        agent_match = re.search(r'agent\s+["\']?(\w+)["\']?', text, re.IGNORECASE)
        agent_name = agent_match.group(1) if agent_match else None
        
        # Extract skill name
        skill_match = re.search(r'(?:skill|function)\s+["\']?(\w+)["\']?', text, re.IGNORECASE)
        skill_name = skill_match.group(1) if skill_match else "custom_skill"
        
        return {
            'intent': 'teach_agent',
            'params': {
                'agent_name': agent_name,
                'skill_name': skill_name,
                'code': ''  # Would need separate input for code
            }
        }
    
    async def _llm_processing(self, user_input: str) -> Dict[str, Any]:
        """Use actual LLM for intent extraction"""
        try:
            if self.provider == "openai" and self.llm_client:
                prompt = f"""
Analyze this user command and extract the intent and parameters.

User Command: {user_input}

Return JSON with:
- intent: One of: create_agent, add_task, create_workflow, teach_agent, list_agents, list_tasks, show_stats, execute, help, unknown
- params: Object with relevant parameters

Examples:
- "create agent named CryptoBot with cryptography capabilities" → {{"intent": "create_agent", "params": {{"name": "CryptoBot", "type": "specialist", "capabilities": ["cryptography"]}}}}
- "add task to calculate fibonacci(10)" → {{"intent": "add_task", "params": {{"name": "Calculate fibonacci", "function": "calculate", "task_params": {{"expression": "fibonacci(10)"}}, "priority": "normal"}}}}
"""
                
                response = self.llm_client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an AI orchestrator that extracts intent from natural language commands. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                
                content = response.choices[0].message.content
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            # Fallback to pattern matching
            return self._pattern_based_processing(user_input)
        
        except Exception as e:
            logger.error(f"Error in LLM processing: {e}")
            return self._pattern_based_processing(user_input)
    
    def generate_response(self, result: Dict[str, Any]) -> str:
        """Generate natural language response"""
        if not result:
            return "I encountered an issue processing that request."
        
        status = result.get('status', 'unknown')
        
        if status == 'success':
            intent = result.get('intent')
            
            if intent == 'create_agent':
                agent_id = result.get('agent_id')
                name = result.get('name')
                return f"✅ Successfully created agent '{name}' (ID: {agent_id})"
            
            elif intent == 'add_task':
                task_id = result.get('task_id')
                name = result.get('name')
                return f"✅ Task '{name}' added (ID: {task_id})"
            
            elif intent == 'create_workflow':
                workflow_id = result.get('workflow_id')
                return f"✅ Workflow '{workflow_id}' created"
            
            elif intent == 'execute':
                tasks_completed = result.get('tasks_completed', 0)
                return f"✅ Executed {tasks_completed} task(s)"
            
            elif intent == 'list_agents':
                agents = result.get('agents', [])
                if agents:
                    agent_list = "\n".join([f"  • {a['name']} ({a['status']})" for a in agents])
                    return f"📋 Active Agents:\n{agent_list}"
                else:
                    return "📋 No agents available"
            
            elif intent == 'list_tasks':
                tasks = result.get('tasks', [])
                if tasks:
                    task_list = "\n".join([f"  • {t['name']} ({t['status']})" for t in tasks])
                    return f"📋 Tasks:\n{task_list}"
                else:
                    return "📋 No tasks in queue"
            
            elif intent == 'show_stats':
                stats = result.get('stats', {})
                return f"📊 Statistics:\n{json.dumps(stats, indent=2)}"
            
            elif intent == 'help':
                return """🤖 Available Commands:
• create agent [named NAME] [with CAPABILITIES]
• add task [to FUNCTION] [with PARAMS]
• create workflow [named NAME]
• teach agent [AGENT] [skill SKILL]
• list agents / show agents
• list tasks / show tasks
• execute / run
• stats / statistics
• help"""
            
            else:
                return f"✅ {result.get('message', 'Operation completed')}"
        
        elif status == 'error':
            error = result.get('error', 'Unknown error')
            return f"❌ Error: {error}"
        
        else:
            return f"⚠️  Status: {status}"


# ============================================
# LLM-POWERED ORCHESTRATOR
# ============================================

class LLMPoweredOrchestrator:
    """
    Natural language controlled orchestrator
    Uses LLM to understand user intent and control the system
    """
    
    def __init__(self, llm_api_key: str = None, llm_model: str = "gpt-3.5-turbo", llm_provider: str = "openai"):
        # Initialize LLM interface
        self.llm = LLMInterface(api_key=llm_api_key, model=llm_model, provider=llm_provider)
        
        # Initialize GhostGoat orchestrator
        self.orchestrator = IntegratedOrchestrator(
            llm_provider=llm_provider if llm_api_key else "mock",
            llm_model=llm_model,
            llm_api_key=llm_api_key
        )
        
        # Local agent and task management
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.workflows: Dict[str, Workflow] = {}
        
        # Statistics
        self.stats = {
            'agents_created': 0,
            'tasks_completed': 0,
            'workflows_executed': 0
        }
        
        logger.info("LLM-Powered Orchestrator initialized")
    
    async def process_command(self, user_input: str) -> Dict[str, Any]:
        """
        Process natural language command
        Returns result dictionary
        """
        logger.info(f"Processing command: {user_input}")
        
        # Use LLM to extract intent
        intent_data = await self.llm.process(user_input)
        intent = intent_data.get('intent')
        params = intent_data.get('params', {})
        
        logger.info(f"Extracted intent: {intent}, params: {params}")
        
        # Execute intent
        try:
            if intent == 'create_agent':
                result = await self._create_agent(params)
            
            elif intent == 'add_task':
                result = await self._add_task(params)
            
            elif intent == 'create_workflow':
                result = await self._create_workflow(params)
            
            elif intent == 'teach_agent':
                result = await self._teach_agent(params)
            
            elif intent == 'list_agents':
                result = await self._list_agents()
            
            elif intent == 'list_tasks':
                result = await self._list_tasks()
            
            elif intent == 'show_stats':
                result = await self._show_stats()
            
            elif intent == 'execute':
                result = await self._execute_tasks()
            
            elif intent == 'help':
                result = {'status': 'success', 'intent': 'help', 'message': 'Help displayed'}
            
            else:
                # Try to use GhostGoat orchestrator for unknown intents
                result = await self._orchestrate_with_ghostgoat(user_input)
            
            result['intent'] = intent
            return result
        
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'intent': intent
            }
    
    async def _create_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent"""
        agent_id = f"agent_{int(time.time())}"
        name = params.get('name', f"Agent_{int(time.time())}")
        agent_type = AgentType(params.get('type', 'worker'))
        capabilities = params.get('capabilities', ['general'])
        
        agent = Agent(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            capabilities=capabilities
        )
        
        self.agents[agent_id] = agent
        self.stats['agents_created'] += 1
        
        # Also add to GhostGoat orchestrator agent profiles
        from llm_orchestrator import AgentProfile
        
        capability_enums = []
        for cap in capabilities:
            try:
                capability_enums.append(AgentCapability(cap))
            except ValueError:
                capability_enums.append(AgentCapability.GENERAL)
        
        self.orchestrator.agent_profiles[name] = AgentProfile(
            name=name,
            host="127.0.0.1",
            port=8000 + len(self.orchestrator.agent_profiles),
            capabilities=capability_enums,
            status="available"
        )
        
        return {
            'status': 'success',
            'agent_id': agent_id,
            'name': name,
            'type': agent_type.value,
            'capabilities': capabilities
        }
    
    async def _add_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new task"""
        task_id = f"task_{int(time.time())}"
        name = params.get('name', 'Task')
        function = params.get('function', 'general')
        task_params = params.get('task_params', {})
        priority = params.get('priority', 'normal')
        
        task = Task(
            task_id=task_id,
            name=name,
            function=function,
            task_params=task_params,
            priority=priority
        )
        
        self.tasks[task_id] = task
        
        return {
            'status': 'success',
            'task_id': task_id,
            'name': name,
            'function': function,
            'priority': priority
        }
    
    async def _create_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a workflow"""
        workflow_id = params.get('workflow_id', f"workflow_{int(time.time())}")
        tasks = params.get('tasks', [])
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name=workflow_id,
            tasks=tasks
        )
        
        self.workflows[workflow_id] = workflow
        
        return {
            'status': 'success',
            'workflow_id': workflow_id,
            'tasks': tasks
        }
    
    async def _teach_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Teach an agent a new skill"""
        agent_name = params.get('agent_name')
        skill_name = params.get('skill_name')
        code = params.get('code', '')
        
        if agent_name and agent_name in self.agents:
            agent = self.agents[agent_name]
            if skill_name not in agent.capabilities:
                agent.capabilities.append(skill_name)
        
        return {
            'status': 'success',
            'message': f"Taught {skill_name} to {agent_name or 'agent'}"
        }
    
    async def _list_agents(self) -> Dict[str, Any]:
        """List all agents"""
        agents_list = [
            {
                'agent_id': a.agent_id,
                'name': a.name,
                'type': a.agent_type.value,
                'status': a.status.value,
                'capabilities': a.capabilities,
                'tasks_completed': a.tasks_completed
            }
            for a in self.agents.values()
        ]
        
        return {
            'status': 'success',
            'agents': agents_list
        }
    
    async def _list_tasks(self) -> Dict[str, Any]:
        """List all tasks"""
        tasks_list = [
            {
                'task_id': t.task_id,
                'name': t.name,
                'function': t.function,
                'status': t.status.value,
                'priority': t.priority,
                'assigned_agent': t.assigned_agent
            }
            for t in self.tasks.values()
        ]
        
        return {
            'status': 'success',
            'tasks': tasks_list
        }
    
    async def _show_stats(self) -> Dict[str, Any]:
        """Show statistics"""
        return {
            'status': 'success',
            'stats': {
                **self.stats,
                'total_agents': len(self.agents),
                'total_tasks': len(self.tasks),
                'total_workflows': len(self.workflows),
                'idle_agents': len([a for a in self.agents.values() if a.status == AgentStatus.IDLE]),
                'pending_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
            }
        }
    
    async def _execute_tasks(self) -> Dict[str, Any]:
        """Execute pending tasks"""
        pending_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        
        if not pending_tasks:
            return {
                'status': 'success',
                'message': 'No pending tasks',
                'tasks_completed': 0
            }
        
        completed = 0
        for task in pending_tasks:
            result = await self._execute_task(task)
            if result.get('success'):
                completed += 1
        
        self.stats['tasks_completed'] += completed
        
        return {
            'status': 'success',
            'tasks_completed': completed,
            'total_pending': len(pending_tasks)
        }
    
    async def _execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        
        # Find available agent
        available_agents = [
            a for a in self.agents.values()
            if a.status == AgentStatus.IDLE and task.function in a.capabilities
        ]
        
        if not available_agents:
            # Use GhostGoat orchestrator for execution
            try:
                result = await self.orchestrator.orchestrate(task.name)
                task.status = TaskStatus.COMPLETED if result.get('final_result', {}).get('success') else TaskStatus.FAILED
                task.result = result
                return {'success': True, 'result': result}
            except Exception as e:
                task.status = TaskStatus.FAILED
                return {'success': False, 'error': str(e)}
        
        # Assign to agent
        agent = available_agents[0]
        agent.status = AgentStatus.BUSY
        task.assigned_agent = agent.agent_id
        
        try:
            # Execute task based on function
            if task.function == 'calculate':
                result = self._execute_calculate(task.task_params)
            elif task.function == 'analyze':
                result = self._execute_analyze(task.task_params)
            elif task.function == 'process_text':
                result = self._execute_process_text(task.task_params)
            else:
                # Use GhostGoat orchestrator
                result = await self.orchestrator.orchestrate(task.name)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            agent.tasks_completed += 1
            agent.status = AgentStatus.IDLE
            
            return {'success': True, 'result': result}
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            agent.status = AgentStatus.IDLE
            return {'success': False, 'error': str(e)}
    
    def _execute_calculate(self, params: Dict[str, Any]) -> Any:
        """Execute calculation task"""
        expression = params.get('expression', '')
        try:
            # Safe evaluation (in production, use a proper math parser)
            result = eval(expression, {"__builtins__": {}}, {})
            return {'result': result, 'expression': expression}
        except Exception as e:
            return {'error': str(e), 'expression': expression}
    
    def _execute_analyze(self, params: Dict[str, Any]) -> Any:
        """Execute analysis task"""
        return {'status': 'analyzed', 'params': params}
    
    def _execute_process_text(self, params: Dict[str, Any]) -> Any:
        """Execute text processing task"""
        return {'status': 'processed', 'params': params}
    
    async def _orchestrate_with_ghostgoat(self, user_input: str) -> Dict[str, Any]:
        """Use GhostGoat orchestrator for complex queries"""
        try:
            result = await self.orchestrator.orchestrate(user_input)
            return {
                'status': 'success',
                'result': result,
                'message': 'Executed via GhostGoat orchestrator'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def interactive_mode(self):
        """Run in interactive mode"""
        print("🤖 LLM-Powered Orchestrator - Interactive Mode")
        print("Type 'exit' or 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Process command
                result = await self.process_command(user_input)
                
                # Generate and display response
                response = self.llm.generate_response(result)
                print(response)
                print()
            
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


# ============================================
# MAIN
# ============================================

async def main():
    """Main entry point"""
    import os
    
    # Get LLM configuration from environment
    llm_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    
    # Create orchestrator
    orchestrator = LLMPoweredOrchestrator(
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_provider=llm_provider
    )
    
    # Run interactive mode
    await orchestrator.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
