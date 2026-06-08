#!/usr/bin/env python3
"""Web search tool for GhostGoat"""
import os
import sys

def web_search(query: str) -> str:
    """Search the web using Ollama Cloud"""
    try:
        from openai import OpenAI
        api_key = os.getenv("OLLAMA_API_KEY")
        base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
        
        if not api_key:
            return "No API key. Set OLLAMA_API_KEY in .env"
        
        client = OpenAI(api_key=api_key, base_url=f"{base_url}/v1")
        
        response = client.chat.completions.create(
            model="gpt-oss:120b-cloud",
            messages=[{
                "role": "system",
                "content": "You are a helpful web search assistant. Search for the user's query and return the top results with URLs."
            }, {
                "role": "user", 
                "content": f"Web search for: {query}\n\nReturn top 3 results with title, URL, brief summary."
            }],
            temperature=0.3, max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Search error: {e}"

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "latest AI news"
    print(web_search(query))