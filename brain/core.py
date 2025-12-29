from brain.memory import Memory
from brain.optimizer import Optimizer
from brain.reasoning_core import ReasoningCore
from brain.interpreter import interpret_command
# brain/core.py

# Optional imports
try:
    from brain.devtools import DevTools
    HAS_DEVTOOLS = True
except ImportError:
    HAS_DEVTOOLS = False
    DevTools = None

try:
    from brain.embedding_memory import EmbeddingMemory
    HAS_EMBEDDING_MEMORY = True
except ImportError:
    HAS_EMBEDDING_MEMORY = False
    EmbeddingMemory = None

# Optional skills registry import
try:
    from skills.registry import registry
    HAS_SKILLS = True
except ImportError:
    # Create a minimal registry if skills module doesn't exist
    registry = {}
    HAS_SKILLS = False

class Brain:
    def __init__(self, memory_path="brain_memory.db", optimizer_path="brain_optimizer.db"):
        # Initialize components with error handling
        try:
            self.memory = Memory(memory_path)
        except Exception as e:
            print(f"[Brain] Memory initialization failed: {e}")
            self.memory = None
        
        try:
            self.reasoner = ReasoningCore()
        except Exception as e:
            print(f"[Brain] ReasoningCore initialization failed: {e}")
            self.reasoner = None
        
        try:
            self.optimizer = Optimizer(optimizer_path)
        except Exception as e:
            print(f"[Brain] Optimizer initialization failed: {e}")
            self.optimizer = None
        
        try:
            # EmbeddingMemory requires sentence-transformers, make it optional
            if HAS_EMBEDDING_MEMORY and EmbeddingMemory:
                self.embed_memory = EmbeddingMemory()
            else:
                self.embed_memory = None
        except Exception as e:
            print(f"[Brain] EmbeddingMemory initialization failed (optional): {e}")
            self.embed_memory = None

        # Auto-load repository embeddings when the brain starts
        try:
            if hasattr(self, 'preload_repo'):
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
        
        # Save to memory if available
        if self.memory:
            try:
                self.memory.save(user_id, user_input, str(plan))
            except Exception as e:
                print(f"[Brain] Memory save failed: {e}")

        # Execute the plan
        result = self.execute_plan(user_id, plan)

        # Reflect on the reasoning if reasoner available
        if self.reasoner:
            try:
                reflection = self.reasoner.reflect(user_input, plan, result)
                print("Reasoning reflection:\n", reflection)
            except Exception as e:
                print(f"[Brain] Reflection failed: {e}")
        
        # Observe with optimizer if available
        if self.optimizer:
            try:
                self.optimizer.observe(user_id, user_input, result)
            except Exception as e:
                print(f"[Brain] Optimizer observe failed: {e}")

        # Store vector memory (embedding) if available
        if self.embed_memory:
            try:
                # EmbeddingMemory.store() expects (user_id, key, text)
                self.embed_memory.store(user_id, "input", user_input)
            except Exception as e:
                print(f"[Brain] Embedding memory store failed: {e}")

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
            if not HAS_SKILLS:
                return f"Skills module not available. Cannot create skill '{skill_name}'."
            try:
                from skills.skill_writer import create_skill
                return create_skill(skill_name, registry)
            except ImportError:
                return f"Skills module not available. Cannot create skill '{skill_name}'."

        # Run an existing dynamic skill
        if action == "run_skill" and skill_name:
            if not HAS_SKILLS or not registry:
                return f"Skills registry not available. Cannot run skill '{skill_name}'."
            if skill_name in registry:
                try:
                    result = registry[skill_name]()
                    return f"Executed {skill_name}: {result}"
                except Exception as e:
                    return f"Error executing {skill_name}: {e}"
            else:
                return f"Skill '{skill_name}' not found in registry."

        # Fallback: match keywords
        if HAS_SKILLS and registry:
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
