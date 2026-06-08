#!/usr/bin/env python3
"""
Quick test script for GhostGoat LLM Orchestrator
"""

import asyncio


def test_basic():
    """Test basic orchestrator functionality"""
    print("Testing GhostGoat LLM Orchestrator...")
    print("=" * 50)
    
    try:
        # Test 1: Import
        print("\n1. Testing imports...")
        from core.brain.agents.tool_agent import LLMOrchestrator  # TODO: was llm_orchestrator LLMOrchestrator
        from core.brain.agents.tool_agent import LLMPoweredOrchestrator  # TODO: was llm_powered_orchestrator LLMPoweredOrchestrator
        from core.brain.agents.tool_agent import create_orchestrator  # TODO: was orchestrator_integration create_orchestrator
        print("   ✅ All imports successful")
        
        # Test 2: Create orchestrator
        print("\n2. Creating orchestrator...")
        orchestrator = LLMOrchestrator(llm_provider="mock")
        print("   ✅ Orchestrator created")
        
        # Test 3: Get status
        print("\n3. Getting status...")
        status = orchestrator.get_status()
        print(f"   ✅ Status retrieved: {status['llm_provider']}")
        
        # Test 4: LLM-Powered Orchestrator
        print("\n4. Testing LLM-Powered Orchestrator...")
        llm_orch = LLMPoweredOrchestrator(llm_api_key=None)
        print("   ✅ LLM-Powered Orchestrator created")
        
        # Test 5: Process a simple command
        print("\n5. Processing command...")
        result = asyncio.run(llm_orch.process_command("list agents"))
        print(f"   ✅ Command processed: {result.get('intent')}")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_basic())
    exit(0 if success else 1)