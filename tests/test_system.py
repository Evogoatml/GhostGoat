#!/usr/bin/env python3
"""
Simple test to verify the GhostGoat system is working
"""
import asyncio
from config.unified_config import init_config
from core.memory.unified_memory import create_memory
from frameworks.llm.multi_llm import create_llm, LLMMessage

async def main():
    print("=" * 60)
    print("GHOSTGOAT SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Configuration
    print("\n[1/3] Testing configuration...")
    config = init_config()
    print(f"✓ Config loaded: LLM={config.llm.provider.value}, Memory={config.memory.backend.value}")
    
    # Test 2: Memory system
    print("\n[2/3] Testing memory system...")
    memory = create_memory(config.memory)
    
    # Store some test data
    id1 = await memory.store("Python is a programming language")
    id2 = await memory.store("JavaScript is used for web development")
    print(f"✓ Stored 2 memories: {id1[:8]}..., {id2[:8]}...")
    
    # Retrieve
    results = await memory.retrieve("programming", top_k=2)
    print(f"✓ Retrieved {len(results)} memories")
    
    # Get stats
    stats = await memory.get_stats()
    print(f"✓ Memory stats: {stats}")
    
    # Test 3: LLM interface
    print("\n[3/3] Testing LLM interface...")
    llm = create_llm(config.llm)
    messages = [LLMMessage(role="user", content="Hello!")]
    response = await llm.generate(messages)
    print(f"✓ LLM response: {response.content[:50]}...")
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    import os
    # Use mock LLM and in-memory backend for testing
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["MEMORY_BACKEND"] = "memory"
    
    asyncio.run(main())
