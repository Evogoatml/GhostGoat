#!/usr/bin/env python3
"""
Comprehensive Test and Audit Suite
Tests all components with security validation
"""

import sys
import time
import json
import hashlib
from typing import Dict, List, Tuple
from datetime import datetime

sys.path.insert(0, '/home/claude/quantum-adaptive-crypto-orchestrator/core')
sys.path.insert(0, '/home/claude/quantum-adaptive-crypto-orchestrator')

try:
    from crypto_engine.mutating_cipher import MutatingCryptoEngine, CipherType
    from ai_orchestrator.agentic_rag import AIOrchestrator, DecisionContext
    from network_security.adaptive_defense import AdaptiveNetworkDefense, PortConfig
    from main import QuantumAdaptiveSystem
    IMPORTS_OK = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


class TestResult:
    """Test result container"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.details = {}
        self.duration = 0.0
    
    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"{status} | {self.name} ({self.duration:.3f}s)\n    {self.message}"


class SecurityAuditor:
    """Security audit functionality"""
    
    @staticmethod
    def audit_encryption_strength(encrypted_data: Dict) -> Dict[str, any]:
        """Audit encryption implementation"""
        results = {
            "cipher_chain_length": len(encrypted_data['metadata'].cipher_chain),
            "uses_manchester": encrypted_data['metadata'].manchester_layers > 0,
            "manchester_layers": encrypted_data['metadata'].manchester_layers,
            "key_derivation": encrypted_data['metadata'].key_derivation,
            "rolling_code_entropy": len(set(encrypted_data['metadata'].rolling_code)),
            "timestamp_recent": time.time() - encrypted_data['metadata'].timestamp < 60
        }
        
        # Calculate security score
        score = 0
        if results['cipher_chain_length'] >= 2:
            score += 30
        if results['uses_manchester']:
            score += 20
        if results['manchester_layers'] >= 2:
            score += 15
        if results['key_derivation'] == 'scrypt':
            score += 20
        if results['rolling_code_entropy'] > 20:
            score += 15
        
        results['security_score'] = min(100, score)
        results['assessment'] = (
            "EXCELLENT" if score >= 80 else
            "GOOD" if score >= 60 else
            "ADEQUATE" if score >= 40 else
            "WEAK"
        )
        
        return results
    
    @staticmethod
    def audit_bit_integrity(data: bytes) -> Dict:
        """Audit bit-level integrity"""
        if not data:
            return {"valid": False, "reason": "Empty data"}
        
        # Entropy check
        byte_counts = {}
        for byte in data:
            byte_counts[byte] = byte_counts.get(byte, 0) + 1
        
        unique_bytes = len(byte_counts)
        entropy_ratio = unique_bytes / len(data)
        
        # Parity check
        parity = 0
        for byte in data:
            parity ^= byte
        
        # Pattern detection
        has_patterns = False
        for i in range(len(data) - 3):
            if data[i] == data[i+1] == data[i+2] == data[i+3]:
                has_patterns = True
                break
        
        return {
            "valid": entropy_ratio > 0.1 and not has_patterns,
            "entropy_ratio": entropy_ratio,
            "unique_bytes": unique_bytes,
            "total_bytes": len(data),
            "parity": parity,
            "patterns_detected": has_patterns
        }


class ComprehensiveTestSuite:
    """Main test suite"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.auditor = SecurityAuditor()
    
    def run_all_tests(self) -> Dict:
        """Run all tests and return summary"""
        print("=" * 70)
        print("QUANTUM-ADAPTIVE CRYPTO ORCHESTRATOR - TEST & AUDIT SUITE")
        print("=" * 70)
        print()
        
        if not IMPORTS_OK:
            print("ERROR: Cannot import required modules")
            return {"error": "Import failure"}
        
        # Module tests
        self.test_crypto_engine()
        self.test_ai_orchestrator()
        self.test_network_defense()
        self.test_integrated_system()
        
        # Security audits
        self.audit_encryption_security()
        self.audit_ai_decisions()
        
        # Performance tests
        self.performance_benchmark()
        
        return self.generate_report()
    
    def test_crypto_engine(self):
        """Test mutating crypto engine"""
        print("\n" + "=" * 70)
        print("CRYPTO ENGINE TESTS")
        print("=" * 70)
        
        # Test 1: Basic encryption/decryption
        result = TestResult("Crypto: Basic Encrypt/Decrypt")
        start = time.time()
        try:
            engine = MutatingCryptoEngine()
            plaintext = b"Test message for encryption validation"
            
            encrypted = engine.encrypt_mutating(plaintext)
            decrypted = engine.decrypt_mutating(encrypted)
            
            result.passed = plaintext == decrypted
            result.message = f"Encrypted {len(plaintext)} bytes, successfully decrypted"
            result.details = {
                "plaintext_size": len(plaintext),
                "ciphertext_size": len(encrypted['ciphertext']),
                "cipher_chain": encrypted['metadata'].cipher_chain
            }
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
        
        # Test 2: Multiple cipher chains
        result = TestResult("Crypto: Multiple Cipher Chains")
        start = time.time()
        try:
            engine = MutatingCryptoEngine()
            plaintext = b"Testing multiple encryption rounds"
            
            # Test with different chains
            chains = [
                [CipherType.AES_256_GCM],
                [CipherType.CHACHA20_POLY1305],
                [CipherType.AES_256_GCM, CipherType.CHACHA20_POLY1305]
            ]
            
            all_passed = True
            for chain in chains:
                encrypted = engine.encrypt_mutating(plaintext, chain)
                decrypted = engine.decrypt_mutating(encrypted)
                if plaintext != decrypted:
                    all_passed = False
                    break
            
            result.passed = all_passed
            result.message = f"Tested {len(chains)} cipher configurations"
            result.details = {"configurations_tested": len(chains)}
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
        
        # Test 3: Manchester encoding
        result = TestResult("Crypto: Manchester Encoding")
        start = time.time()
        try:
            from crypto_engine.mutating_cipher import ManchesterEncoder
            
            encoder = ManchesterEncoder()
            test_data = b"Manchester test data 12345"
            
            encoded = encoder.encode(test_data)
            decoded = encoder.decode(encoded)
            
            result.passed = test_data == decoded
            result.message = f"Encoded {len(test_data)} → {len(encoded)} → {len(decoded)} bytes"
            result.details = {
                "original_size": len(test_data),
                "encoded_size": len(encoded),
                "expansion_ratio": len(encoded) / len(test_data)
            }
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
        
        # Test 4: Integrity validation
        result = TestResult("Crypto: Integrity Validation")
        start = time.time()
        try:
            engine = MutatingCryptoEngine()
            
            valid_data = b"Valid encrypted data" * 10
            corrupted_data = b"\x00" * 100
            
            valid_check = engine.validate_integrity(valid_data)
            corrupted_check = engine.validate_integrity(corrupted_data)
            
            result.passed = valid_check and not corrupted_check
            result.message = f"Valid: {valid_check}, Corrupted: {corrupted_check}"
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
    
    def test_ai_orchestrator(self):
        """Test AI orchestrator"""
        print("\n" + "=" * 70)
        print("AI ORCHESTRATOR TESTS")
        print("=" * 70)
        
        # Test 1: Decision making
        result = TestResult("AI: Crypto Pipeline Decisions")
        start = time.time()
        try:
            orchestrator = AIOrchestrator("/tmp/test_orchestrator.pkl")
            
            # High security context
            context_high = DecisionContext(
                threat_level=9,
                data_sensitivity=10,
                performance_priority=3,
                network_state={},
                historical_attacks=["sql_injection"]
            )
            
            decision = orchestrator.decide_crypto_pipeline(context_high)
            recommendation = decision['recommendation']
            
            result.passed = (
                recommendation['cipher_strategy'] == 'multi_layer' and
                recommendation['use_manchester']
            )
            result.message = f"Recommended: {recommendation['cipher_strategy']}"
            result.details = recommendation
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
        
        # Test 2: Learning capability
        result = TestResult("AI: Learning from Experience")
        start = time.time()
        try:
            orchestrator = AIOrchestrator("/tmp/test_learning.pkl")
            initial_vectors = len(orchestrator.vector_db.vectors)
            
            orchestrator.learn_from_attack("ddos", "mitigated", {"duration": "5min"})
            orchestrator.learn_from_success("multi_layer", "prevented breach")
            
            final_vectors = len(orchestrator.vector_db.vectors)
            
            result.passed = final_vectors > initial_vectors
            result.message = f"Vectors: {initial_vectors} → {final_vectors}"
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
        
        # Test 3: RAG retrieval
        result = TestResult("AI: RAG Knowledge Retrieval")
        start = time.time()
        try:
            orchestrator = AIOrchestrator("/tmp/test_rag.pkl")
            
            query = "What encryption is best for high threat?"
            memories = orchestrator.rag_system.retrieve_relevant_knowledge(query, top_k=3)
            
            result.passed = len(memories) > 0
            result.message = f"Retrieved {len(memories)} relevant memories"
            result.details = {"query": query, "results": len(memories)}
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
    
    def test_network_defense(self):
        """Test network defense"""
        print("\n" + "=" * 70)
        print("NETWORK DEFENSE TESTS")
        print("=" * 70)
        
        # Test 1: Port configuration
        result = TestResult("Network: Port Configuration")
        start = time.time()
        try:
            defense = AdaptiveNetworkDefense()
            
            defense.configure_port(PortConfig(
                port=8888,
                is_honeypot=True,
                real_backend=None,
                sandbox_enabled=False,
                service_banner="HTTP test"
            ))
            
            result.passed = 8888 in defense.port_configs
            result.message = f"Configured {len(defense.port_configs)} ports"
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
        
        # Test 2: Threat analysis
        result = TestResult("Network: Threat Detection")
        start = time.time()
        try:
            defense = AdaptiveNetworkDefense()
            
            from network_security.adaptive_defense import ConnectionAttempt
            
            # Simulate malicious attempt
            attempt = ConnectionAttempt(
                source_ip="192.168.1.100",
                source_port=12345,
                target_port=22,
                timestamp=time.time(),
                protocol="tcp",
                payload_snippet=b"SELECT * FROM users WHERE 1=1 OR 1=1"
            )
            
            threat_score = defense.threat_analyzer.analyze_connection(attempt)
            
            result.passed = threat_score > 0
            result.message = f"Detected threat score: {threat_score}/100"
            result.details = {"threat_score": threat_score}
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
    
    def test_integrated_system(self):
        """Test integrated system"""
        print("\n" + "=" * 70)
        print("INTEGRATED SYSTEM TESTS")
        print("=" * 70)
        
        # Test 1: End-to-end encryption
        result = TestResult("Integration: Adaptive Encrypt/Decrypt")
        start = time.time()
        try:
            system = QuantumAdaptiveSystem()
            
            plaintext = b"Integrated system test message with sensitive data"
            
            encrypted = system.adaptive_encrypt(
                plaintext,
                sensitivity=8,
                performance_priority=5,
                threat_context={'threat_level': 7}
            )
            
            decrypted = system.adaptive_decrypt(encrypted)
            
            result.passed = plaintext == decrypted
            result.message = f"Adaptive encryption with AI decision-making"
            result.details = {
                "size": len(plaintext),
                "cipher": encrypted['metadata'].cipher_chain,
                "ai_recommendation": encrypted['ai_decision']['recommendation']['cipher_strategy']
            }
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
    
    def audit_encryption_security(self):
        """Audit encryption security"""
        print("\n" + "=" * 70)
        print("SECURITY AUDITS")
        print("=" * 70)
        
        result = TestResult("Audit: Encryption Strength")
        start = time.time()
        try:
            system = QuantumAdaptiveSystem()
            plaintext = b"Security audit test data"
            
            encrypted = system.adaptive_encrypt(
                plaintext,
                sensitivity=10,
                performance_priority=1,
                threat_context={'threat_level': 10}
            )
            
            audit = self.auditor.audit_encryption_strength(encrypted)
            
            result.passed = audit['security_score'] >= 70
            result.message = f"Security Score: {audit['security_score']}/100 ({audit['assessment']})"
            result.details = audit
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
    
    def audit_ai_decisions(self):
        """Audit AI decision quality"""
        result = TestResult("Audit: AI Decision Quality")
        start = time.time()
        try:
            orchestrator = AIOrchestrator("/tmp/test_audit_ai.pkl")
            
            # Test various scenarios
            scenarios = [
                (9, 10, 2),  # High threat, high sensitivity, low performance
                (2, 3, 10),  # Low threat, low sensitivity, high performance
                (5, 5, 5),   # Balanced
            ]
            
            decisions_made = 0
            appropriate_decisions = 0
            
            for threat, sensitivity, performance in scenarios:
                context = DecisionContext(threat, sensitivity, performance, {}, [])
                decision = orchestrator.decide_crypto_pipeline(context)
                decisions_made += 1
                
                # Validate decision appropriateness
                rec = decision['recommendation']
                if threat > 7 and rec['cipher_strategy'] == 'multi_layer':
                    appropriate_decisions += 1
                elif performance > 7 and rec['cipher_strategy'] in ['aes_256_gcm', 'chacha20_poly1305']:
                    appropriate_decisions += 1
                elif threat <= 7 and performance <= 7:
                    appropriate_decisions += 1
            
            result.passed = appropriate_decisions / decisions_made >= 0.67
            result.message = f"Appropriate decisions: {appropriate_decisions}/{decisions_made}"
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
    
    def performance_benchmark(self):
        """Performance benchmarks"""
        print("\n" + "=" * 70)
        print("PERFORMANCE BENCHMARKS")
        print("=" * 70)
        
        result = TestResult("Performance: Encryption Speed")
        start = time.time()
        try:
            system = QuantumAdaptiveSystem()
            
            test_sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB
            benchmarks = {}
            
            for size in test_sizes:
                plaintext = b"x" * size
                
                t_start = time.time()
                encrypted = system.adaptive_encrypt(plaintext, sensitivity=5, performance_priority=8)
                t_encrypt = time.time() - t_start
                
                t_start = time.time()
                decrypted = system.adaptive_decrypt(encrypted)
                t_decrypt = time.time() - t_start
                
                benchmarks[f"{size}_bytes"] = {
                    "encrypt_ms": t_encrypt * 1000,
                    "decrypt_ms": t_decrypt * 1000,
                    "throughput_mbps": (size / 1024 / 1024) / t_encrypt if t_encrypt > 0 else 0
                }
            
            result.passed = True
            result.message = "Benchmark completed"
            result.details = benchmarks
        except Exception as e:
            result.message = f"Error: {e}"
        result.duration = time.time() - start
        self.results.append(result)
        print(result)
    
    def generate_report(self) -> Dict:
        """Generate final test report"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        # Save detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "success_rate": passed / total if total > 0 else 0
            },
            "tests": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        report_path = "/tmp/qac_test_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        return report


def main():
    """Run test suite"""
    suite = ComprehensiveTestSuite()
    report = suite.run_all_tests()
    
    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)
    
    return 0 if report.get('summary', {}).get('failed', 1) == 0 else 1


if __name__ == "__main__":
    exit(main())
