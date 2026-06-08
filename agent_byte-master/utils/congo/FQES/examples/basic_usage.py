#!/usr/bin/env python3
"""
Basic usage example of FQES system
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.core.simple_fractal import FractalEncoder
    print("✅ Using simplified fractal encoder")
except ImportError as e:
    print(f"❌ Simplified encoder import failed: {e}")
    try:
        from src.core.fractal_encoder import FractalEncoder
        print("✅ Using full fractal encoder")
    except ImportError as e:
        print(f"❌ Full encoder import failed: {e}")
        sys.exit(1)

from src.agents.orchestrator import FractalCompressionCrew, LangGraphOrchestrator

def demonstrate_basic_compression():
    """Demonstrate basic fractal compression"""
    print("=== FQES Basic Compression Demo ===")
    
    # Initialize encoder
    encoder = FractalEncoder()
    
    # Sample data
    data = b"This is test data for fractal compression " * 100
    print(f"Original data size: {len(data)} bytes")
    
    try:
        # Compress with integrity proof
        compressed, proof = encoder.compress_with_proof(data)
        print(f"Compressed size: {len(compressed)} bytes")
        print(f"Compression ratio: {len(compressed)/len(data)*100:.1f}%")
        print(f"Integrity proof: {proof[:32]}...")
        
        # Verify integrity
        verified = encoder.verify_integrity(data, compressed, proof)
        print(f"Integrity verified: {verified}")
    except Exception as e:
        print(f"⚠️ Compression demo skipped: {e}")

def demonstrate_agent_analysis():
    """Demonstrate multi-agent analysis"""
    print("\n=== Multi-Agent Analysis Demo ===")
    
    try:
        crew = FractalCompressionCrew()
        data = b"Sample data for agent analysis" * 10
        
        analysis = crew.analyze_compression_opportunities(data)
        
        for agent, results in analysis.items():
            print(f"{agent}: {results}")
    except Exception as e:
        print(f"⚠️ Agent demo skipped: {e}")

def demonstrate_workflow_orchestration():
    """Demonstrate LangGraph workflow"""
    print("\n=== Workflow Orchestration Demo ===")
    
    try:
        orchestrator = LangGraphOrchestrator()
        workflow = orchestrator.create_compression_workflow()
        
        print(f"Workflow nodes: {workflow.get('nodes', [])}")
        print(f"Workflow edges: {workflow.get('edges', [])}")
    except Exception as e:
        print(f"⚠️ Workflow demo skipped: {e}")

if __name__ == "__main__":
    demonstrate_basic_compression()
    demonstrate_agent_analysis()
    demonstrate_workflow_orchestration()
