import json, os
from pathlib import Path

class ContextMemory:
    def __init__(self, memory_file="~/ADAP/memory_store/context.json"):
        self.path = Path(os.path.expanduser(memory_file))
        if not self.path.exists():
            self.save({"contexts": []})

    def load(self):
        with open(self.path, "r") as f:
            return json.load(f)

    def save(self, data):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
