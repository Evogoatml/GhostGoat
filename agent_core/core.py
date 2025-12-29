from brain.memory import Memory
from brain.optimizer import Optimizer
from brain.reasoning_core import ReasoningCore
from brain.interpreter import interpret_command
from skills.registry import registry
from brain.devtools import DevTools
# brain/core.py
from brain.embedding_memory import EmbeddingMemory

class Brain:
    def __init__(self):
        self.memory = None
        self.reasoner = None
        self.optimizer = None
        self.embed_memory = EmbeddingMemory()  # <-- move it inside __init__

# Auto-load repository embeddings when the brain starts
        try:
            self.preload_repo()
        except Exception as e:
            print(f"[Brain] Repo preload failed: {e}")

        try:
            with open("reasoning_history.json", "r") as f:
                self.prior_reasoning = f.read()
        except FileNotFoundError:
            self.prior_reasoning = None

    def handle(self, user_id: int, user_input: str) -> str:
        print(f"[Brain] Handling command from {user_id}: {user_input}")

        if self.prior_reasoning:
            print(f"\n[Loaded Prior Reasoning]\n{self.prior_reasoning}\n")

        # Interpret the command
        plan = interpret_command(user_input)
        self.memory.save(user_id, user_input, str(plan))

        # Execute the plan
        result = self.execute_plan(user_id, plan)

        # Reflect on the reasoning
        reflection = self.reasoner.reflect(user_input, plan, result)
        print("Reasoning reflection:\n", reflection)
        self.optimizer.observe(user_id, user_input, result)

        # Store vector memory (embedding)
        self.embed_memory.store(user_id, user_input)

        return result

    def execute_plan(self, user_id: int, plan: dict) -> str:
        intent = plan.get("intent", "unknown")
        steps = plan.get("steps", [])
        logs = [plan_to_text(plan), "\n---\nExecuting:\n"]

        for step in steps:
            logs.append(self.run_step(step))

        result = "\n".join(logs)
        reflection = self.reasoner.reflect(intent, plan, result)
        print("Reasoning reflection:\n", reflection)
        return result or "no output"

    def run_step(self, step):
        """Run a single step from a plan."""
        if isinstance(step, dict):
            action = step.get("action", "")
            skill_name = step.get("skill_name", "")
        else:
            action = str(step)
            skill_name = ""

        # Create new skill dynamically
        if action == "create_skill" and skill_name:
            from skills.skill_writer import create_skill
            return create_skill(skill_name, registry)

        # Run an existing dynamic skill
        if action == "run_skill" and skill_name:
            if skill_name in registry:
                try:
                    result = registry[skill_name]()
                    return f"Executed {skill_name}: {result}"
                except Exception as e:
                    return f"Error executing {skill_name}: {e}"
            else:
                return f"Skill '{skill_name}' not found in registry."

        # Fallback: match keywords
        for key, func in registry.items():
            if key.lower() in action.lower():
                try:
                    result = func()
                    return f"Executed {key}: {result}"
                except Exception as e:
                    return f"Error executing {key}: {e}"

        return f"No matching skill found for: {action}"


def plan_to_text(plan: dict) -> str:
    """Convert structured plan dict into a readable step list."""
    intent = plan.get("intent", "unknown")
    steps = plan.get("steps", [])
    lines = [f"Intent: {intent}"]
    for i, step in enumerate(steps, 1):
        action = step.get("action", "unknown")
        desc = step.get("description", "")
        lines.append(f"{i}. {action}: {desc}")
    return "\n".join(lines)
