"""
Claude (Anthropic) Adapter for GhostGoat
"""
import os
from anthropic import Anthropic

class ClaudeLLM:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = Anthropic(api_key=self.api_key)
        self.model = 'claude-3-haiku-20240307'  # Working model!
        self.provider = "anthropic"
    
    async def chat(self, messages):
        """Send messages to Claude"""
        # Convert to Anthropic format
        formatted_messages = []
        for m in messages:
            if hasattr(m, 'role') and hasattr(m, 'content'):
                if m.role != 'system':  # Claude handles system separately
                    formatted_messages.append({
                        "role": m.role,
                        "content": m.content
                    })
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=formatted_messages
        )
        
        return response.content[0].text
    
    def chat_sync(self, messages):
        """Synchronous version"""
        formatted_messages = []
        for m in messages:
            if hasattr(m, 'role') and hasattr(m, 'content'):
                if m.role != 'system':
                    formatted_messages.append({
                        "role": m.role,
                        "content": m.content
                    })
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=formatted_messages
        )
        
        return response.content[0].text

def create_claude_llm():
    return ClaudeLLM()
