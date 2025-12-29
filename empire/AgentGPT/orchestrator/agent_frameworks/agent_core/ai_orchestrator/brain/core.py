import json
from agent_core.brain.memory_sqlite import Memory
from agent_core.brain.optimizer import Optimizer
from agent_core.brain.reasoning_core import ReasoningCore
from agent_core.brain.interpreter import interpret_command, plan_to_text
from agent_core.brain.embedding_memory import EmbeddingMemory
from agent_core.skills.registry import registry
from agent_core.skills.base_skills import run_step 

class AgentCore:
    def __init__(self, db_path="data/brain.db", history_path="data/reasoning_history.json"):
        self.memory = Memory(db_path)
        self.optimizer = Optimizer(db_path)
        self.reasoner = ReasoningCore(memory_path=history_path)
        self.embed_memory = EmbeddingMemory()
        self.prior_reasoning = self._load_prior_reasoning(history_path)

    def _load_prior_reasoning(self, history_path):
        try:
            with open(history_path, "r") as f:
                data = json.load(f)
                return data[-1]["reflection"] if data else None
        except (FileNotFoundError, IndexError, json.JSONDecodeError):
            return None

    def handle(self, user_id: int, user_input: str) -> str:
        plan = interpret_command(user_input)
        self.memory.save(user_id, user_input, str(plan))
        result = self._execute_plan(user_id, plan)
        reflection = self.reasoner.reflect(user_input, plan, result)
        self.optimizer.observe(user_id, user_input, result)
        self.embed_memory.store(user_id, "user_input", user_input)

        return result

    def _execute_plan(self, user_id: int, plan: dict) -> str:
        logs = [plan_to_text(plan), "\n---\nExecuting:\n"]
        for step in plan.get("steps", []):
            logs.append(run_step(step)) 
        result = "\n".join(logs)
        return result or "no output"
