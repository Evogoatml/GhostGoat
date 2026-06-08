"""Creative thinking module for lateral thinking and innovation"""

from abc import ABC, abstractmethod

class BrainModule(ABC):
    """Base class for all brain modules"""
    
    @abstractmethod
    def process(self, query: str) -> str:
        """Process a query and return insights"""
        pass

class CreativeModule(BrainModule):
    """Module for creative, lateral thinking"""
    
    def __init__(self):
        self.creativity_factors = [
            "What if we approached this from a completely different angle?",
            "How would a child solve this problem?",
            "What assumptions are we making that we could challenge?",
            "How might this look in 10 years?",
            "What would happen if we removed all constraints?"
        ]
    
    def process(self, query: str) -> str:
        """Apply creative thinking to the query"""
        import random
        factor = random.choice(self.creativity_factors)
        
        prompt = f"""Apply creative lateral thinking to: {query}
        
Consider this prompt: {factor}

Provide innovative, unconventional approaches or perspectives."""
        
        # Use AI to generate creative response
        return ai_call(
            prompt,
            system="You are a creative thinking specialist who excels at lateral thinking and innovation."
        )[:300]