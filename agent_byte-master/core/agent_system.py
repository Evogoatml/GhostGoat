#!/usr/bin/env python3
"""
Multi-Agent Orchestrator System
Combines CrewAI, AutoGPT-style, and AgentK patterns
Coordinates specialized pentesting agents
"""

import os
import json
import time
import logging
import requests
import threading
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from datetime import datetime
import random

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCcFrJQd1u8cxsKyCZfCxDt7P4lJPwgxWE")
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'

class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"

@dataclass
class Message:
    """Inter-agent message"""
    sender: str
    receiver: str
    content: str
    timestamp: float = field(default_factory=time.time)
    msg_type: str = "text"

@dataclass
class Task:
    """Task for agents"""
    id: str
    description: str
    assigned_to: str = None
    status: str = "pending"
    result: str = ""
    created_at: float = field(default_factory=time.time)
    tools: List[str] = field(default_factory=list)

class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, name: str, role: str, capabilities: List[str]):
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.state = AgentState.IDLE
        self.memory: List[Dict] = []
        self.inbox: List[Message] = []
        self.current_task: Optional[Task] = None
    
    def think(self, prompt: str) -> str:
        """Process input with LLM"""
        raise NotImplementedError
    
    def act(self, action: str) -> str:
        """Execute action"""
        raise NotImplementedError
    
    def remember(self, key: str, value: str):
        self.memory.append({"key": key, "value": value, "time": time.time()})
    
    def recall(self, key: str) -> Optional[str]:
        for m in reversed(self.memory):
            if m["key"] == key:
                return m["value"]
        return None

class LLMAgent(BaseAgent):
    """LLM-powered agent (AutoGPT style)"""
    
    def __init__(self, name: str, role: str, capabilities: List[str], system_prompt: str = ""):
        super().__init__(name, role, capabilities)
        self.system_prompt = system_prompt or f"You are {role}. {name} agent."
        self.max_iterations = 5
        self.loop_count = 0
    
    def think(self, prompt: str) -> str:
        """Think with reflection loop"""
        self.state = AgentState.THINKING
        self.loop_count = 0
        
        while self.loop_count < self.max_iterations:
            full_prompt = f"""{self.system_prompt}

Task: {prompt}

Think step {self.loop_count + 1}/{self.max_iterations}:
- Analyze the task
- Consider what you know
- Plan your response
- Execute

Respond with your analysis and final answer."""

            try:
                resp = self._call_llm(full_prompt)
                self.loop_count += 1
                
                if resp and len(resp) > 50:
                    self.state = AgentState.DONE
                    return resp
                    
            except Exception as e:
                logger.error(f"Think error: {e}")
        
        self.state = AgentState.ERROR
        return f"Thinking limit reached after {self.loop_count} iterations"
    
    def _call_llm(self, prompt: str) -> str:
        try:
            resp = requests.post(
                GEMINI_URL,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048,
                        "stopSequences": ["===TASK DONE==="]
                    }
                },
                timeout=60
            )
            if resp.status_code == 200:
                return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"LLM error: {e}")
        return ""

class CrewAIAgent(BaseAgent):
    """CrewAI-style agent with task hierarchy"""
    
    def __init__(self, name: str, role: str, capabilities: List[str], goal: str = ""):
        super().__init__(name, role, capabilities)
        self.goal = goal
        self.subtasks: List[Task] = []
        self.delegates: List[BaseAgent] = []
    
    def add_delegate(self, agent: BaseAgent):
        """Add subordinate agent"""
        self.delegates.append(agent)
        logger.info(f"{self.name} added delegate: {agent.name}")
    
    def assign_task(self, task: Task):
        """Assign task to delegate"""
        if self.delegates:
            available = random.choice(self.delegates)
            task.assigned_to = available.name
            available.current_task = task
            self.state = AgentState.WAITING
            return f"Assigned to {available.name}"
        return "No delegates available"
    
    def think(self, prompt: str) -> str:
        """Think and decompose task"""
        self.state = AgentState.THINKING
        
        prompt_full = f"""{self.system_prompt if hasattr(self, 'system_prompt') else f'You are {self.role}'}

Goal: {self.goal}

Task: {prompt}

Break this down into subtasks. Return as JSON:
{{"subtasks": [{{"description": "...", "agent_type": "..."}}]}}"""

        try:
            resp = self._call_llm(prompt_full)
            
            try:
                data = json.loads(resp)
                self.subtasks = [
                    Task(id=f"task_{i}", description=s["description"])
                    for i, s in enumerate(data.get("subtasks", []))
                ]
            except:
                self.subtasks = [Task(id="main", description=prompt)]
            
            self.state = AgentState.DONE
            return f"Decomposed into {len(self.subtasks)} subtasks"
            
        except Exception as e:
            self.state = AgentState.ERROR
            return f"Error: {e}"
    
    def _call_llm(self, prompt: str) -> str:
        try:
            resp = requests.post(
                GEMINI_URL,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60
            )
            if resp.status_code == 200:
                return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"LLM error: {e}")
        return ""

class AgentKAgent(BaseAgent):
    """AgentK-style self-improving agent"""
    
    def __init__(self, name: str, role: str, capabilities: List[str]):
        super().__init__(name, role, capabilities)
        self.tools = {}
        self的成功 = 0
        self.failures = 0
        self.tool_history: List[Dict] = []
    
    def register_tool(self, name: str, func: Callable):
        """Register a tool the agent can use"""
        self.tools[name] = func
        logger.info(f"{self.name} registered tool: {name}")
    
    def think(self, prompt: str) -> str:
        """Think with tool usage tracking"""
        self.state = AgentState.THINKING
        
        prompt_full = f"""{self.role}

Available tools: {list(self.tools.keys())}

Task: {prompt}

Decide which tool to use and execute. Report result."""

        result = self._call_llm(prompt_full)
        
        if result:
            self._learn(result)
        
        self.state = AgentState.DONE
        return result or "No result"
    
    def _learn(self, result: str):
        """Self-improve based on results"""
        if len(result) > 10:
            self.success += 1
        else:
            self.failures += 1
        
        self.tool_history.append({
            "result": result[:100],
            "success": len(result) > 10,
            "time": time.time()
        })
        
        logger.info(f"{self.name} stats: {self.success} success, {self.failures} failures")
    
    def _call_llm(self, prompt: str) -> str:
        try:
            resp = requests.post(
                GEMINI_URL,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60
            )
            if resp.status_code == 200:
                return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"LLM error: {e}")
        return ""

class Orchestrator:
    """Coordinates all agents"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_queue: List[Message] = []
        self.tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._init_agents()
    
    def _init_agents(self):
        self.agents = {
            "recon": LLMAgent(
                "recon",
                "Reconnaissance Agent",
                ["nmap", "whois", "dns"],
                "You are a reconnaissance agent. Gather info about targets."
            ),
            "scanner": LLMAgent(
                "scanner",
                "Vulnerability Scanner",
                ["nvd", "cve", "scan"],
                "You find vulnerabilities in systems."
            ),
            "exploiter": LLMAgent(
                "exploiter",
                "Exploitation Agent",
                ["metasploit", "exploit", "shell"],
                "You exploit vulnerabilities to gain access."
            ),
            "post": LLMAgent(
                "post",
                "Post-Exploitation Agent",
                ["privesc", "persistence", "pivot"],
                "You maintain access and escalate privileges."
            ),
            "crew_lead": CrewAIAgent(
                "crew_lead",
                "Crew Leader",
                ["coordination", "delegation"],
                "Coordinate a crew of specialized agents."
            ),
            "agentk": AgentKAgent(
                "agentk",
                "Self-Improving Agent",
                ["learning", "tool_use"],
                "Learn and improve from each task."
            )
        }
        
        logger.info(f"Initialized {len(self.agents)} agents")
    
    def execute_task(self, task: str) -> Dict:
        """Execute task with appropriate agent"""
        task_lower = task.lower()
        
        if "recon" in task_lower or "scan" in task_lower or "find" in task_lower:
            return self._run_agent("recon", task)
        
        if "exploit" in task_lower or "attack" in task_lower:
            return self._run_agent("exploiter", task)
        
        if "privesc" in task_lower or "escalate" in task_lower:
            return self._run_agent("post", task)
        
        if "learn" in task_lower or "improve" in task_lower or "agentk" in task_lower:
            return self._run_agent("agentk", task)
        
        if "crew" in task_lower or "multiple" in task_lower:
            return self._run_crew(task)
        
        return self._run_agent("scanner", task)
    
    def _run_agent(self, agent_name: str, task: str) -> Dict:
        if agent_name not in self.agents:
            return {"error": f"Unknown agent: {agent_name}"}
        
        agent = self.agents[agent_name]
        
        try:
            result = agent.think(task)
            return {
                "agent": agent_name,
                "role": agent.role,
                "result": result[:500],
                "state": agent.state.value
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _run_crew(self, task: str) -> Dict:
        crew = self.agents.get("crew_lead")
        if not crew:
            return {"error": "No crew leader"}
        
        try:
            result = crew.think(task)
            return {
                "agent": "crew_lead",
                "role": "Crew Leader",
                "result": result,
                "subtasks": len(crew.subtasks)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_status(self) -> Dict:
        return {
            "agents": {
                name: {
                    "role": a.role,
                    "state": a.state.value,
                    "capabilities": a.capabilities
                }
                for name, a in self.agents.items()
            }
        }

orchestrator = Orchestrator()

def get_help_text() -> str:
    status = orchestrator.get_status()
    
    text = "<b>Multi-Agent Orchestrator</b>\n\n"
    text += "<b>Active Agents:</b>\n"
    for name, info in status["agents"].items():
        text += f"• {name}: {info['role']} ({info['state']})\n"
    
    text += "\n<b>How it works:</b>\n"
    text += "1. Send a task or question\n"
    text += "2. Orchestrator picks best agent\n"
    text += "3. Agent processes with LLM\n"
    text += "4. Returns result + context\n\n"
    
    text += "<b>Examples:</b>\n"
    text += "• How do I find vulnerabilities?\n"
    text += "• Scan target.com for exploits\n"
    text += "• Explain privilege escalation\n"
    text += "• Use crew to test APIs"
    
    return text

def process_query(query: str) -> str:
    """Process user query through orchestrator"""
    
    parts = query.lower().split()
    
    if any(w in parts for w in ["help", "status", "list", "agents"]):
        return get_help_text()
    
    if any(w in parts for w in ["what", "how", "explain", "what is"]):
        return orchestrator._run_agent("scanner", query)
    
    result = orchestrator.execute_task(query)
    
    if "error" in result:
        return f"❌ Error: {result['error']}"
    
    response = f"<b>Agent: {result.get('agent', 'unknown')}</b>\n"
    response += f"<i>{result.get('role', '')}</i>\n\n"
    response += f"{result.get('result', 'No result')[:1000]}"
    
    return response

def main():
    logger.info("Testing orchestrator...")
    
    status = orchestrator.get_status()
    print("Agents:", list(status["agents"].keys()))
    
    test_tasks = [
        "How does SQL injection work?",
        "Explain privilege escalation",
        "Find vulnerabilities in web app",
    ]
    
    for task in test_tasks:
        print(f"\n--- {task} ---")
        result = orchestrator.execute_task(task)
        print(f"Agent: {result.get('agent')}")
        print(f"Result: {result.get('result', result.get('error'))[:200]}...")

if __name__ == '__main__':
    main()