"""
GhostGoat Legacy Agent Executors
Wraps the original AgentK, AgentGPT, CrewAI, SuperAGI, SwarmsAI
functionality as proper TaskExecutor subclasses for AgentNetwork.
"""
import asyncio
import re
import subprocess
from typing import Any, Dict
from core.agents.agent_core.agent_network import TaskExecutor


def _ai_call(prompt: str, system: str = None, model: str = "llama3.2", timeout: int = 30) -> str:
    full = f"System: {system}\n" if system else ""
    full += f"User: {prompt}\nAI:"
    try:
        r = subprocess.run(
            ["ollama", "run", model, full],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        return f"[AI error: {e}]"


class AgentKExecutor(TaskExecutor):
    """Skill specialist — fast execution, code, crypto, port scans."""

    def __init__(self, model: str = "llama3.2"):
        super().__init__("AgentK", "skill", ["hash", "scan", "system", "crypto"])
        self.model = model

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = payload.get("goal", "")
        tl = task.lower()

        if any(w in tl for w in ["hash", "sha", "md5"]):
            result = _ai_call(f"Calculate hash of: {task}", system="You compute cryptographic hashes.", model=self.model)
            return {"success": True, "result": result}

        if "port" in tl or "scan" in tl:
            target = re.findall(r'([a-z0-9.-]+\.[a-z]{2,})', tl)
            if target:
                try:
                    r = subprocess.run(
                        ["nmap", "-sV", target[0]],
                        capture_output=True, text=True, timeout=60
                    )
                    return {"success": True, "stdout": r.stdout[:2000], "stderr": r.stderr[:500], "returncode": r.returncode}
                except Exception as e:
                    return {"success": False, "error": str(e)}

        if "system" in tl or "cpu" in tl or "mem" in tl:
            try:
                r = subprocess.run("free -h && df -h", shell=True, capture_output=True, text=True)
                return {"success": True, "stdout": r.stdout}
            except Exception as e:
                return {"success": False, "error": str(e)}

        result = _ai_call(f"Execute skill: {task}", system="You are a skill executor.", model=self.model)
        return {"success": True, "result": result}


class AgentGPTExecutor(TaskExecutor):
    """Web researcher — search and synthesis via LLM."""

    def __init__(self, model: str = "llama3.2"):
        super().__init__("AgentGPT", "research", ["search", "synthesize", "web"])
        self.model = model

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = payload.get("goal", "")
        query = _ai_call(f"Search query for: {task}", system="You optimize search queries.", model=self.model, timeout=15)
        results = _ai_call(f"Web search results for: {query[:80]}", system="You are a search engine.", model=self.model, timeout=15)
        synthesis = _ai_call(
            f"Task: {task}\n\nResults:\n{results}\n\nSynthesize:",
            system="You synthesize research from multiple sources.", model=self.model, timeout=20
        )
        return {"success": True, "result": synthesis[:500] if synthesis else results[:500]}


class CrewAIExecutor(TaskExecutor):
    """Multi-role pipeline: researcher → analyst → writer."""

    def __init__(self, model: str = "llama3.2"):
        super().__init__("CrewAI", "pipeline", ["research", "analyze", "write", "multi_role"])
        self.model = model

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = payload.get("goal", "")
        roles = [
            ("Researcher", f"Find info on: {task}"),
            ("Analyst", f"Analyze: {task}"),
            ("Writer", f"Write about: {task}"),
        ]
        pipeline = []
        for role, prompt in roles:
            result = _ai_call(prompt, system=f"You are {role}. Complete your part.", model=self.model, timeout=20)
            pipeline.append(f"[{role}]: {result[:200]}")
        return {"success": True, "result": "\n\n".join(pipeline)}


class SuperAGIExecutor(TaskExecutor):
    """Goal decomposer — recursive planning."""

    def __init__(self, model: str = "llama3.2"):
        super().__init__("SuperAGI", "planner", ["decompose", "plan", "gap_analysis"])
        self.model = model

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = payload.get("goal", "")
        sub = _ai_call(
            f'Decompose into sub-tasks: {task}\nJSON: {{"tasks": ["t1", "t2"]}}',
            system="You decompose complex goals into executable steps.", model=self.model, timeout=20
        )
        gaps = _ai_call(
            f"What capabilities are missing for: {task}?",
            system="You identify capability gaps.", model=self.model, timeout=15
        )
        return {"success": True, "result": f"Goal: {task}\n\nPlan: {sub[:300]}\n\nGaps: {gaps[:200]}"}


class SwarmsAIExecutor(TaskExecutor):
    """Parallel workers — emergent consensus."""

    def __init__(self, model: str = "llama3.2"):
        super().__init__("SwarmsAI", "swarm", ["parallel", "consensus", "multi_perspective"])
        self.model = model

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = payload.get("goal", "")
        perspectives = [
            f"Answer from technical perspective: {task}",
            f"Answer from practical perspective: {task}",
            f"Answer from creative perspective: {task}",
        ]

        async def _run_perspective(p):
            return _ai_call(p, system="You are an expert. Answer directly.", model=self.model, timeout=20)

        results = await asyncio.gather(*[_run_perspective(p) for p in perspectives])
        combined = "\n\n".join(f"[Worker {i+1}]: {r[:200]}" for i, r in enumerate(results))

        consensus = _ai_call(
            f"Aggregate:\n{combined}\n\nConsensus:",
            system="You form consensus from multiple perspectives.", model=self.model, timeout=20
        )
        return {"success": True, "result": consensus[:500] if consensus else combined[:500]}

