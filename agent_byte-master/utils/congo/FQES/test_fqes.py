#!/usr/bin/env python3
"""
Comprehensive FQES Test Script
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_core_functionality():
    """Test core FQES functionality"""
    print("🧪 Testing Core FQES Functionality")
    print("=" * 40)
    
    try:
        from src.core.fractal_encoder import FractalEncoder, ManchesterEncoder, LatticeCrypto
        
        # Test FractalEncoder
        encoder = FractalEncoder()
        test_data = b"Test data for fractal compression " * 100
        
        print(f"Original data size: {len(test_data)} bytes")
        
        # Test compression with proof
        compressed, proof = encoder.compress_with_proof(test_data)
        print(f"Compressed size: {len(compressed)} bytes")
        print(f"Compression ratio: {len(compressed)/len(test_data)*100:.1f}%")
        print(f"Proof generated: {proof[:32]}...")
        
        # Test integrity verification
        verified = encoder.verify_integrity(test_data, compressed, proof)
        print(f"Integrity verified: {verified}")
        
        print("✅ Core functionality test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Core functionality test FAILED: {e}")
        return False

def test_agent_orchestration():
    """Test agent orchestration"""
    print("\n🧪 Testing Agent Orchestration")
    print("=" * 40)
    
    try:
        from src.agents.orchestrator import FractalCompressionCrew, LangGraphOrchestrator
        
        # Test agent crew
        crew = FractalCompressionCrew()
        test_data = b"Sample data for agent analysis" * 50
        
        analysis = crew.analyze_compression_opportunities(test_data)
        print("Agent analysis results:")
        for agent, result in analysis.items():
            print(f"  {agent}: {result}")
        
        # Test workflow orchestration
        orchestrator = LangGraphOrchestrator()
        workflow = orchestrator.create_compression_workflow()
        print(f"Workflow created: {workflow}")
        
        print("✅ Agent orchestration test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Agent orchestration test FAILED: {e}")
        return False

def test_quantum_resistance():
    """Test quantum resistance components"""
    print("\n🧪 Testing Quantum Resistance")
    print("=" * 40)
    
    try:
        from src.quantum.deception_fractals import DeceptionFractalGenerator
        
        generator = DeceptionFractalGenerator()
        base_pattern = b"base_pattern_data"
        
        # Generate deceptive fractal branches
        branches = generator.generate_infinite_branches(base_pattern)
        print(f"Generated {len(branches)} deceptive fractal branches")
        
        # Test confusion matrix
        matrix = generator.quantum_confusion_matrix(base_pattern)
        print(f"Quantum confusion matrix shape: {matrix.shape if hasattr(matrix, 'shape') else 'n/a'}")
        
        print("✅ Quantum resistance test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Quantum resistance test FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("🎯 FQES Comprehensive Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 3
    
    # Run tests
    if test_core_functionality():
        tests_passed += 1
    
    if test_agent_orchestration():
        tests_passed += 1
    
    if test_quantum_resistance():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 ALL TESTS PASSED! FQES is ready for development.")
        print("\n🚀 Next steps:")
        print("1. Review ARCHITECTURE.md for implementation guidance")
        print("2. Follow IMPLEMENTATION_PLAN.md for phased development")
        print("3. Begin Phase 1: Mathematical foundations")
    else:
        print("⚠️ Some tests failed. Check the implementation.")
    
    return tests_passed == tests_total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
