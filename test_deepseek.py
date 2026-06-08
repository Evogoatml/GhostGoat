#!/usr/bin/env python3
"""
Simple test to demonstrate DeepSeek integration with GhostGoat concepts
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

def test_deepseek_direct():
    """Test DeepSeek API directly"""
    print("Testing DeepSeek API directly...")
    
    try:
        from openai import OpenAI
        
        # Get API key from environment
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ DEEPSEEK_API_KEY not found in environment")
            return False
            
        print(f"✓ Found DEEPSEEK_API_KEY: {api_key[:10]}...")
        
        # Initialize DeepSeek client
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        # Test completion
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": "Say 'Hello from DeepSeek!' in one sentence."}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        print(f"✓ DeepSeek response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ DeepSeek test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_gorilla_style_thinking():
    """Test a simplified version of GhostGoat's thinking with DeepSeek"""
    print("\nTesting GhostGoat-style thinking with DeepSeek...")
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        
        # Simulate GhostGoat's multi-perspective thinking
        prompt = """You are an AI assistant with multiple reasoning perspectives:
        1. Analytical: Break down problems logically
        2. Creative: Think outside the box
        3. Practical: Focus on actionable solutions
        
        Problem: How can I improve my website security?
        
        Provide perspectives from each viewpoint, then synthesize."""
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are an AI assistant with analytical, creative, and practical reasoning perspectives."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.8
        )
        
        result = response.choices[0].message.content
        print(f"✓ Multi-perspective response received ({len(result)} characters)")
        print(f"Preview: {result[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Gorilla-style thinking test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("GhostGoat DeepSeek Integration Test")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success1 = test_deepseek_direct()
    success2 = test_with_gorilla_style_thinking()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED - DeepSeek integration is working!")
        print("\nTo use DeepSeek with GhostGoat:")
        print("1. Your .env already has DEEPSEEK_API_KEY and LLM_PROVIDER=deepseek")
        print("2. The orchestrator bot needs to be updated to use DeepSeek")
        print("3. See the simple integration pattern above")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
