#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '.')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

print("=== Environment Variables ===")
print(f"OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'not set')}")
print(f"LLM_MODEL: {os.getenv('LLM_MODEL', 'not set')}")

print("\n=== Testing GhostGoat LLM Configuration ===")
try:
    from config.unified_config import LLMConfig, LLMProvider
    from frameworks.llm.multi_llm import MultiLLM
    from frameworks.llm.multi_llm import LLMMessage
    
    # Load configuration
    config = LLMConfig.from_env()
    print(f"Config provider: {config.provider}")
    print(f"Config provider value: {config.provider.value}")
    print(f"Config model: {config.model}")
    print(f"Has API key: {bool(config.api_key)}")
    
    # Test the comparison directly
    print(f"\nDirect comparison:")
    print(f"  config.provider == LLMProvider.OPENAI: {config.provider == LLMProvider.OPENAI}")
    print(f"  config.provider.value == LLMProvider.OPENAI.value: {config.provider.value == LLMProvider.OPENAI.value}")
    
    # Initialize MultiLLM
    print(f"\nInitializing MultiLLM...")
    llm = MultiLLM(config)
    print(f"Interface type: {type(llm.interface).__name__}")
    
    # Test a simple generation
    print(f"\nTesting LLM generation...")
    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Say hello in one word.")
    ]
    
    import asyncio
    async def test_generation():
        try:
            result = await llm.generate(messages, temperature=0.3, max_tokens=10)
            if hasattr(result, 'content'):
                print(f"LLM Response: {result.content}")
            else:
                print(f"LLM Response: {result}")
            return True
        except Exception as e:
            print(f"Error during generation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    success = asyncio.run(test_generation())
    if success:
        print(f"\n✅ GhostGoat LLM is working correctly!")
    else:
        print(f"\n❌ GhostGoat LLM test failed")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
