import asyncio
import litellm
from pathlib import Path
from pycrdt import Doc, Map, Array
from .identity import HolonIdentity
from .synapse import Synapse
from .tools import HolonTools
from .config import config
import structlog

logger = structlog.get_logger()

class Holon:
    def __init__(self, path: Path, crdt: Doc):
        self.path = path
        self.identity = HolonIdentity(path)
        self.synapse = Synapse(path)
        self.crdt = crdt
        self.tools = HolonTools()
        self._register()

    def _register(self):
        agents: Map = self.crdt.get_or_insert("agents", Map)
        agents[self.identity.id] = {
            "path": str(self.path),
            "role": self.synapse.config["role"],
            "status": "ONLINE",
            "capabilities": self.synapse.config["capabilities"],
            "last_seen": asyncio.get_event_loop().time()
        }

    async def run(self):
        while True:
            try:
                tasks = self._pull_attractive_tasks()
                for task in tasks:
                    if await self._should_handle(task):
                        await self._execute(task)
                await asyncio.sleep(8)
            except Exception as e:
                logger.error("holon_error", holon=str(self.path), error=str(e))

    def _pull_attractive_tasks(self):
        tasks: Array = self.crdt.get_or_insert("tasks", Array)
        return [t for t in tasks if any(cap in t.get("required_caps", []) for cap in self.synapse.config["capabilities"])]

    async def _should_handle(self, task: dict) -> bool:
        # Simple attraction logic — can be upgraded with embeddings
        return task.get("status") == "pending"

    async def _execute(self, task: dict):
        system_prompt = f"""You are {self.synapse.config['role']} holon in the Nexus Lattice.
Synapse: {self.synapse.config}
Task: {task}
Use tools to solve it. Propose changes via CRDT."""
        
        response = await litellm.acompletion(
            model=config.llm_model,
            messages=[{"role": "system", "content": system_prompt}],
            temperature=config.llm_temperature
        )
        # Process response, apply patches, propose to CRDT, etc.
        task["status"] = "completed"
        task["result"] = response.choices[0].message.content
        logger.info("task_completed", holon=str(self.path), task_id=task.get("id"))
