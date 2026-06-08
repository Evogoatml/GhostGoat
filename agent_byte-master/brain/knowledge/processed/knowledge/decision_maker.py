"""Decision maker stub."""

class SymbolicDecisionMaker:
    def __init__(self, agent_id, storage=None, config=None):
        self.agent_id = agent_id
        self.storage = storage
        self.config = config or {}

    def decide(self, state, q_values, exploration_rate):
        return 0, {'confidence': 0.5, 'reasoning': 'stub'}

    def update(self, experience):
        pass
