#!/usr/bin/env python3
"""
Simple test to verify LLM orchestration works with mock provider.
No API keys needed.
"""

import asyncio
import sys
import os

# Add the GhostGoat directory to path
sys.path.insert(0, '/home/popic/GhostGoat')

from core.orchestrator.llm_orchestrator import LLMOrchestrator

async def test_mock_llm():
    """Test the LLM orchestrator with mock provider."""
    print("Testing LLM Orchestrator with Mock Provider...")
    
    # Create orchestrator with mock provider - no API keys needed
    orchestrator = LLMOrchestrator(
        llm_provider="mock",  # This uses the built-in mock LLM
        llm_model="mock-model"
    )
    
    # Test a simple query
    result = await orchestrator.orchestrate(
        "Explain the concept of machine learning in simple terms"
    )
    
    print("\n=== ORCHESTRATION RESULT ===")
    print(f"Query: {result['query']}")
    print(f"Summary: {result['final_result'].get('summary', 'No summary')}")
    print(f"Success: {result['final_result'].get('success', False)}")
    print(f"Number of tasks: {len(result['tasks'])}")
    
    # Show task details
    for i, task in enumerate(result['tasks']):
        print(f"\nTask {i+1}: {task['description']}")
        print(f"  Agent: {task.get('assigned_agent', 'None')}")
        print(f"  Status: {task['status']}")
    
    return result

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_mock_llm())
    print("\n✅ Test completed successfully!")