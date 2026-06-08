import os
import json
import time
import asyncio
import hashlib
from dotenv import load_dotenv
from pydantic import BaseModel
from rich.console import Console

load_dotenv()

# Use relative imports when running as a package
from ..tools.registry import ToolRegistry
from ..memory.memory import Memory
from .planner import Planner

console = Console()


class Step(BaseModel):
    thought: str
    action: str | None = None
    input: dict | None = None
    output: str | None = None
    timestamp: float = time.time()


def hash_step(step: Step) -> str:
    return hashlib.sha256(step.model_dump_json().encode()).hexdigest()


async def run(task: str, max_iters: int = 12):
    registry = ToolRegistry()
    memory = Memory()
    planner = Planner()
    steps: list[Step] = []

    console.rule(f"[bold cyan]{os.getenv('AGENT_NAME', 'EvoGoat')}[/] -- task: {task}")

    for i in range(max_iters):
        ctx = memory.recall(task, k=5)
        thought, tool_name, tool_input = await planner.decide(task, ctx)
        step = Step(thought=thought, action=tool_name, input=tool_input, timestamp=time.time())

        if tool_name:
            tool = registry.get(tool_name)
            result = await tool(**(tool_input or {}))
            step.output = result[:4000] if isinstance(result, str) else json.dumps(result)[:4000]
            memory.store_snippet(task, step.thought, step.output)

        steps.append(step)
        console.print(
            f"[bold]#{i+1}[/] {step.thought}\n"
            f"  -> {step.action} {step.input}\n"
            f"  <- {str(step.output)[:200]}"
        )

        runs_dir = os.path.join(os.path.dirname(__file__), '..', 'runs')
        os.makedirs(runs_dir, exist_ok=True)
        h = hash_step(step)
        run_file = os.path.join(runs_dir, f"{int(step.timestamp)}_{i}_{h[:8]}.json")
        with open(run_file, "w") as f:
            f.write(step.model_dump_json())

        if planner.done(step):
            break

    console.rule("[green]done")
    return steps


if __name__ == "__main__":
    import sys
    asyncio.run(run(" ".join(sys.argv[1:]) or "Research and summarize the latest FAISS tips"))
