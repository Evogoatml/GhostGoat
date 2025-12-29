# adap/agent_core/memory.py

import os, json

class AgentMemory:
    def __init__(self, path="../data/memory.db"):
        self.path = path
        self.memory = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.memory = json.load(f)
        else:
            self.memory = {}

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.memory, f, indent=2)

    def get(self, key, default=None):
        return self.memory.get(key, default)

    def set(self, key, value):
        self.memory[key] = value
        self.save()

    def append_log(self, entry):
        self.memory.setdefault("logs", []).append(entry)
        self.save()
