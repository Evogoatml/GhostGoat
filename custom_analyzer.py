"""Example of a dynamically loaded custom agent"""

from abc import ABC, abstractmethod

class AgentBase(ABC):
    """Base class for all agents"""
    
    @abstractmethod
    def run(self, task: str) -> str:
        """Execute the agent on a task"""
        pass

class CustomAnalyzerAgent(AgentBase):
    """A custom agent for specialized analysis tasks"""
    
    def __init__(self):
        self.analysis_tools = [
            "trend_analysis",
            "pattern_recognition", 
            "risk_assessment",
            "opportunity_identification"
        ]
    
    def run(self, task: str) -> str:
        """Run specialized analysis on the task"""
        # Determine what type of analysis to perform based on the task
        task_lower = task.lower()
        
        if "trend" in task_lower or "time" in task_lower:
            analysis_type = "trend_analysis"
        elif "risk" in task_lower or "danger" in task_lower:
            analysis_type = "risk_assessment"
        elif "opportunity" in task_lower or "potential" in task_lower:
            analysis_type = "opportunity_identification"
        else:
            analysis_type = "pattern_recognition"
        
        # Create analysis prompt
        prompt = f"""Perform {analysis_type.replace('_', ' ')} on the following task:
        
Task: {task}

Provide:
1. Key insights and findings
2. Recommended actions
3. Potential risks or considerations
4. Confidence level in analysis (0-100%)
"""
        
        # Use AI to perform the analysis
        result = ai_call(
            prompt,
            system=f"You are an expert analyst specializing in {analysis_type.replace('_', ' ')}. "
                  f"Provide clear, actionable insights based on the task."
        )
        
        return f"[{analysis_type.upper()} ANALYSIS]\n{result[:400]}"