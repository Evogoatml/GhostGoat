import json
import os
from datetime import datetime

class ReasoningCore:
    def __init__(self, memory_path="data/reasoning_history.json"):
        self.memory_path = memory_path
        if not os.path.exists(self.memory_path):
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, "w") as f:
                json.dump([], f)

    def _load(self):
        with open(self.memory_path, "r") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.memory_path, "w") as f:
            json.dump(data, f, indent=2)

    def reflect(self, query, plan, result):
        reflection = {
            "query": query,
            "plan": plan,
            "result": result,
            "reflection": self._generate_reflection(query, result),
            "timestamp": datetime.utcnow().isoformat(),
        }

        data = self._load()
        data.append(reflection)
        self._save(data)
        return reflection["reflection"]

    def _generate_reflection(self, query, result):
        if "error" in result.lower():
            return f"Reassess plan for '{query}': Prior step caused an error, simplify or retry safely."
        elif "no matching skill" in result.lower():
            return f"Expand skill registry to cover missing intent for: '{query}'."
        elif "executing" in result.lower():
            return f"Successful reasoning path for: '{query}'. Reinforce logic flow."
        else:
            return f"Generic reflection for '{query}'. Monitor result quality next iteration."
