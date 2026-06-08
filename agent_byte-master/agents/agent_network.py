"""GhostGoat AgentNetwork — Fleet Management for Swarm and Deployable Bots."""
import asyncio, json, time, uuid, logging, subprocess
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class AgentProfile:
    agent_id: str
    name: str
    role: str
    status: str = "idle"
    capabilities: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)
    total_tasks: int = 0
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class TaskExecutor:
    def __init__(self, name: str, role: str, capabilities: Optional[List[str]] = None, model: str = "llama3.2"):
        self.name = name; self.role = role; self.capabilities = capabilities or []
        self.logger = logging.getLogger(f"agent.{name}")
        self.model = model

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Anthropic API if key available, else stub."""
        import os
        goal = payload.get("goal", "")
        prompt = payload.get("input", goal)
        system = f"You are {self.name}, a {self.role} agent. Complete the task directly and concisely."
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            try:
                import urllib.request, json as _json
                body = _json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 512,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode()
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=body,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = _json.loads(resp.read())
                    text = data["content"][0]["text"]
                    return {"success": True, "result": text, "agent_id": self.name}
            except Exception as e:
                return {"error": str(e), "success": False, "agent_id": self.name}
        else:
            return {"success": True, "result": f"[stub] {self.name} received: {prompt[:100]}", "agent_id": self.name}

class ShellExecutor(TaskExecutor):
    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cmd = payload.get("command", "")
        if not cmd: return {"error": "No command", "success": False}
        timeout = payload.get("timeout", 30)
        try:
            proc = await asyncio.create_subprocess_exec(*cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {"success": proc.returncode == 0, "stdout": stdout.decode(errors="replace"),
                    "stderr": stderr.decode(errors="replace"), "returncode": proc.returncode}
        except asyncio.TimeoutError:
            proc.kill(); await proc.wait()
            return {"error": "Timeout", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

class PythonExecutor(TaskExecutor):
    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        code = payload.get("code", "")
        if not code: return {"error": "No code", "success": False}
        try:
            local_ns = {}
            exec(code, {"__builtins__": __builtins__}, local_ns)
            return {"success": True, "result": local_ns.get("result")}
        except Exception as e:
            return {"error": str(e), "success": False}

class ResearchExecutor(TaskExecutor):
    def __init__(self, knowledge_source: Optional[Any] = None):
        super().__init__("researcher", "research", ["search", "synthesize", "retrieve"])
        self.knowledge_source = knowledge_source
    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "result": f"Research: {payload.get('query', '')[:100]}"}

class AgentNetwork:
    def __init__(self, max_agents: int = 50):
        self.network_id = f"net-{uuid.uuid4().hex[:8]}"
        self.max_agents = max_agents
        self.profiles: Dict[str, AgentProfile] = {}
        self.executors: Dict[str, TaskExecutor] = {}
        self.logger = logger
        self.logger.info("AgentNetwork initialized: %s", self.network_id)

    def register(self, agent_id: str, executor: TaskExecutor, capabilities: Optional[List[str]] = None) -> AgentProfile:
        if len(self.profiles) >= self.max_agents:
            raise RuntimeError("At capacity")
        profile = AgentProfile(agent_id=agent_id, name=executor.name, role=executor.role,
                               capabilities=capabilities or executor.capabilities)
        self.profiles[agent_id] = profile
        self.executors[agent_id] = executor
        self.logger.info("Registered: %s (%s)", agent_id, executor.role)
        return profile

    def spawn_default_fleet(self):
        for aid, ex in [("shell-1", ShellExecutor("shell-runner", "execution", ["shell", "bash"])),
                        ("python-1", PythonExecutor("py-runner", "execution", ["python", "code"])),
                        ("research-1", ResearchExecutor()),
                        ("analyst-1", TaskExecutor("analyst", "analysis", ["analyze", "summarize"])),
                        ("supervisor-1", TaskExecutor("supervisor", "oversight", ["recover", "delegate"]))]:
            self.register(aid, ex)

    def spawn_legacy_fleet(self):
        """Register legacy AgentK/GPT/CrewAI/SuperAGI/SwarmsAI agents."""
        from core.agents.specialists.legacy_agents import (
            AgentKExecutor, AgentGPTExecutor, CrewAIExecutor,
            SuperAGIExecutor, SwarmsAIExecutor,
        )
        self.register("agentk-1", AgentKExecutor())
        self.register("agentgpt-1", AgentGPTExecutor())
        self.register("crewai-1", CrewAIExecutor())
        self.register("superagi-1", SuperAGIExecutor())
        self.register("swarmsai-1", SwarmsAIExecutor())

    def spawn_full_fleet(self):
        """Register both default and legacy agents."""
        self.spawn_default_fleet()
        self.spawn_legacy_fleet()

    async def dispatch(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if agent_id not in self.executors: return {"error": f"Agent {agent_id} not found", "success": False}
        profile = self.profiles[agent_id]
        profile.status = "busy"; profile.current_task = payload.get("goal", "unknown")
        profile.last_heartbeat = time.time(); start = time.time()
        try:
            result = await self.executors[agent_id].execute(payload)
            profile.total_tasks += 1
            profile.success_rate = ((profile.success_rate * (profile.total_tasks - 1)) + (1.0 if result.get("success") else 0.0)) / profile.total_tasks
        except Exception as e:
            result = {"error": str(e), "success": False}
        finally:
            profile.status = "idle"; profile.current_task = None; profile.last_heartbeat = time.time()
        result["agent_id"] = agent_id; result["latency_ms"] = (time.time() - start) * 1000
        return result

    async def dispatch_swarm(self, payload: Dict[str, Any], role_filter: Optional[str] = None, max_parallel: int = 5) -> List[Dict[str, Any]]:
        eligible = [aid for aid, p in self.profiles.items() if p.status == "idle" and (not role_filter or p.role == role_filter)]
        selected = eligible[:max_parallel]
        if not selected: return [{"error": "No idle agents", "success": False}]
        return await asyncio.gather(*[self.dispatch(aid, payload) for aid in selected])

    def get_fleet_status(self) -> Dict[str, Any]:
        return {"network_id": self.network_id,
                "agents": [{"agent_id": p.agent_id, "name": p.name, "role": p.role, "status": p.status,
                            "capabilities": p.capabilities, "total_tasks": p.total_tasks,
                            "success_rate": round(p.success_rate, 3)} for p in self.profiles.values()],
                "capacity": f"{len(self.profiles)}/{self.max_agents}"}

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        return self.profiles.get(agent_id)



