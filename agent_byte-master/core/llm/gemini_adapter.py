"""
Gemini (Google AI) Adapter for GhostGoat
Using NEW google-genai SDK
"""
import os
from google import genai
from google.genai import types

class GeminiLLM:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.client = genai.Client(api_key=self.api_key)
        self.model = 'gemini-2.0-flash-exp'  # Latest free model
        self.provider = "gemini"
    
    async def chat(self, messages):
        """Send messages to Gemini"""
        # Convert messages to simple prompt
        if isinstance(messages, list):
            prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        else:
            prompt = str(messages)
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        return response.text
    
    def chat_sync(self, messages):
        """Synchronous version"""
        if isinstance(messages, list):
            prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        else:
            prompt = str(messages)
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        return response.text

def create_gemini_llm():
    return GeminiLLM()
