from agent_core.cognitive_engine import CognitiveEngine

class DecisionController:
    def __init__(self):
        self.engine = CognitiveEngine()

    def execute(self, context):
        return self.engine.reason(context)
