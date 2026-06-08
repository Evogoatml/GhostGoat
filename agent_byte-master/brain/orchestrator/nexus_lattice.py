import asyncio
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional
import pycrdt
import psutil
from datetime import datetime
import litellm  # or your preferred LLM client (OpenAI, Anthropic, local, etc.)
# Optional: langgraph for specific structured workflows inside a holon

class HolonIdentity:
    """Cryptographic DNA for every folder-agent."""
    def __init__(self, path: Path):
        self.path = path
        self.id = hashlib.blake2b(str(path).encode()).hexdigest()[:32]
        self.key = hashlib.blake2b(self.id.encode()).digest()

    def sign(self, data: dict) -> str:
        # Expand with real lattice crypto / post-quantum later
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode() + self.key).hexdigest()

class Synapse:
    """Executable AGENT.md — now a living config + behavior spec."""
    def __init__(self, holon_path: Path):
        self.path = holon_path / "AGENT.md"
        self.config: Dict = {}
        self.load_or_create()

    def load_or_create(self):
        if not self.path.exists():
            self.config = {
                "role": self.path.parent.name,
                "capabilities": ["code_edit", "test", "review"],
                "goals": ["maintain_sovereignty", "attract_relevant_tasks"],
                "tools": ["read_file", "write_patch", "run_tests"],
                "parent": str(self.path.parent.parent) if self.path.parent.parent != Path.cwd() else None
            }
            self.save()
        else:
            # Parse markdown + embedded YAML/JSON frontmatter
            content = self.path.read_text()
            # Simple parser - expand as needed
            try:
                # Look for JSON block in markdown
                import re
                json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    self.config = json.loads(json_match.group(1))
                else:
                    self.config = {"role": self.path.parent.name, "status": "loaded"}
            except:
                self.config = {"role": self.path.parent.name, "status": "error"}

    def save(self):
        content = f"# Holon Synapse: {self.path.parent.name}\n\n```json\n{json.dumps(self.config, indent=2)}\n```\n"
        self.path.write_text(content)

class Holon:
    def __init__(self, path: Path, crdt: pycrdt.Doc):
        self.path = path
        self.identity = HolonIdentity(path)
        self.synapse = Synapse(path)
        self.crdt = crdt  # Reference to shared lattice
        self.local_memory = {}  # Can be backed by vector store later

    def activate(self):
        # Register in shared CRDT
        agents_map = self.crdt.get_or_insert("agents", pycrdt.Map)
        agents_map[self.identity.id] = {
            "path": str(self.path),
            "role": self.synapse.config["role"],
            "status": "ONLINE",
            "last_pulse": datetime.now().isoformat()
        }

    async def run(self):
        """Main holon loop — pulls tasks that match its capabilities."""
        while True:
            # Query CRDT for attractive tasks (no central queue)
            tasks = self._query_relevant_tasks()
            for task in tasks:
                if await self._should_handle(task):
                    await self._execute_task(task)
            await asyncio.sleep(10)  # Adaptive backoff possible

    def _query_relevant_tasks(self):
        # Example: tasks that mention this holon's role or files in its folder
        tasks = []
        try:
            task_list = self.crdt.get_or_insert("tasks", pycrdt.Array)
            for task in task_list:
                if self.synapse.config["role"] in task.get("tags", []):
                    tasks.append(task)
        except:
            pass
        return tasks

    async def _should_handle(self, task: dict) -> bool:
        # Simple check - expand with LLM reasoning later
        return task.get("status") == "pending"

    async def _execute_task(self, task: dict):
        # LLM call with tools + context from CRDT + local files
        try:
            response = await litellm.acompletion(
                model="anthropic/claude-3-7-sonnet",  # or local
                messages=[{"role": "system", "content": self._build_system_prompt()}],
                # tools=...  # file ops, git, tests, etc.
            )
            # Propose patch → other holons can review/vote via CRDT
            task["status"] = "completed"
            task["result"] = response.choices[0].message.content
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)

    def _build_system_prompt(self) -> str:
        return f"You are a {self.synapse.config['role']} agent. Capabilities: {self.synapse.config['capabilities']}"

class NexusLattice:
    def __init__(self, root: Path):
        self.root = root
        self.crdt = pycrdt.Doc()  # Shared sovereign memory
        self.holons: Dict[str, Holon] = {}
        self.bootstrap()

    def bootstrap(self):
        """Genesis runs once → spawns holons → becomes dormant observer."""
        for path in self.root.iterdir():
            if path.is_dir() and not path.name.startswith('.'):
                holon = Holon(path, self.crdt)
                self.holons[str(path)] = holon
                holon.activate()  # Registers self in CRDT, loads synapse

        # Publish lattice metadata
        self.crdt.get_or_insert("lattice", pycrdt.Map)["holons"] = list(self.holons.keys())
        print(f"🌌 Nexus Lattice seeded with {len(self.holons)} holons")

    async def pulse(self):
        """Lightweight observer — no heavy orchestration."""
        while True:
            await self.health_check()
            await asyncio.sleep(30)  # Very low duty cycle

    async def health_check(self):
        # Distributed: each holon reports its own health into CRDT
        load = psutil.cpu_percent()
        if load > 85:
            # Broadcast signal — holons self-throttle or spawn sub-holons
            self.crdt.get_or_insert("alerts", pycrdt.Array).append({
                "type": "high_load",
                "timestamp": datetime.now().isoformat()
            })

if __name__ == "__main__":
    # Quick test
    lattice = NexusLattice(Path.cwd())
    print(f"Lattice active with {len(lattice.holons)} holons")
    
    # Run health pulse
    asyncio.run(lattice.pulse())
