#!/usr/bin/env python3
"""
Quantum-Adaptive Crypto Orchestrator - Main Integration
Combines mutating crypto, AI orchestration, and adaptive network defense
"""

import sys
import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Add core modules to path
sys.path.insert(0, '/home/claude/quantum-adaptive-crypto-orchestrator/core')

try:
    from crypto_engine.mutating_cipher import (
        MutatingCryptoEngine, CipherType, EncryptionMetadata
    )
    from ai_orchestrator.agentic_rag import (
        AIOrchestrator, DecisionContext, SimpleVectorDB
    )
    from network_security.adaptive_defense import (
        AdaptiveNetworkDefense, PortConfig, ConnectionAttempt
    )
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import core modules: {e}")
    MODULES_AVAILABLE = False


class QuantumAdaptiveSystem:
    """
    Main integrated system combining:
    - Mutating encryption engine
    - AI-driven decision orchestration
    - Adaptive network defense
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if not MODULES_AVAILABLE:
            raise ImportError("Core modules not available")
        
        self.config = config or self._default_config()
        
        # Initialize components
        print("Initializing Quantum-Adaptive System...")
        
        self.crypto_engine = MutatingCryptoEngine()
        print("  ✓ Crypto engine initialized")
        
        self.ai_orchestrator = AIOrchestrator(
            vector_db_path=self.config.get('vector_db_path', '/tmp/qac_memory.pkl')
        )
        print("  ✓ AI orchestrator initialized")
        
        self.network_defense = AdaptiveNetworkDefense()
        print("  ✓ Network defense initialized")
        
        self.operation_log: list = []
        print("  ✓ System ready\n")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default system configuration"""
        return {
            "vector_db_path": "/tmp/qac_memory.pkl",
            "auto_learn": True,
            "mutation_frequency": "dynamic",
            "default_threat_level": 5,
            "enable_network_defense": False  # Disabled by default (requires ports)
        }
    
    def adaptive_encrypt(self, 
                        plaintext: bytes,
                        sensitivity: int = 5,
                        performance_priority: int = 5,
                        threat_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Intelligently encrypt data using AI-driven cipher selection
        
        Args:
            plaintext: Data to encrypt
            sensitivity: Data sensitivity (0-10)
            performance_priority: Performance importance (0-10)
            threat_context: Optional threat context info
            
        Returns:
            Dictionary with encrypted data and full metadata
        """
        start_time = time.time()
        
        # Create decision context
        context = DecisionContext(
            threat_level=threat_context.get('threat_level', self.config['default_threat_level']) 
                        if threat_context else self.config['default_threat_level'],
            data_sensitivity=sensitivity,
            performance_priority=performance_priority,
            network_state=threat_context.get('network_state', {}) if threat_context else {},
            historical_attacks=threat_context.get('attacks', []) if threat_context else []
        )
        
        # Get AI recommendation
        decision = self.ai_orchestrator.decide_crypto_pipeline(context)
        recommendation = decision['recommendation']
        
        # Map recommendation to cipher types
        cipher_chain = self._map_recommendation_to_ciphers(recommendation)
        
        # Encrypt with mutating engine
        encrypted = self.crypto_engine.encrypt_mutating(plaintext, cipher_chain)
        
        # Add AI decision metadata
        encrypted['ai_decision'] = decision
        encrypted['encryption_time'] = time.time() - start_time
        
        # Log operation
        self._log_operation("encrypt", {
            "data_size": len(plaintext),
            "cipher_chain": [c.value for c in cipher_chain],
            "threat_level": context.threat_level,
            "sensitivity": sensitivity,
            "time": encrypted['encryption_time']
        })
        
        # Learn from operation if auto-learning enabled
        if self.config['auto_learn']:
            self.ai_orchestrator.learn_from_success(
                strategy=recommendation['cipher_strategy'],
                outcome=f"encrypted {len(plaintext)} bytes in {encrypted['encryption_time']:.3f}s"
            )
        
        return encrypted
    
    def adaptive_decrypt(self, encrypted_data: Dict[str, Any]) -> bytes:
        """Decrypt data encrypted with adaptive_encrypt"""
        start_time = time.time()
        
        plaintext = self.crypto_engine.decrypt_mutating(encrypted_data)
        
        # Validate integrity
        if not self.crypto_engine.validate_integrity(plaintext):
            raise ValueError("Data integrity validation failed")
        
        decryption_time = time.time() - start_time
        
        self._log_operation("decrypt", {
            "data_size": len(plaintext),
            "time": decryption_time
        })
        
        return plaintext
    
    def _map_recommendation_to_ciphers(self, recommendation: Dict) -> list:
        """Map AI recommendation to actual cipher implementations"""
        strategy = recommendation['cipher_strategy']
        
        if strategy == "multi_layer":
            return [CipherType.AES_256_GCM, CipherType.CHACHA20_POLY1305]
        elif strategy == "aes_256_gcm":
            return [CipherType.AES_256_GCM]
        elif strategy == "chacha20_poly1305":
            return [CipherType.CHACHA20_POLY1305]
        else:
            return [CipherType.AES_256_GCM]  # Fallback
    
    def configure_network_defense(self, 
                                  honeypot_ports: list = None,
                                  forward_ports: list = None,
                                  sandbox_ports: list = None):
        """
        Configure network defense topology
        
        Args:
            honeypot_ports: List of (port, service_type) tuples
            forward_ports: List of (listen_port, backend_host, backend_port) tuples
            sandbox_ports: List of (port, service_type) tuples
        """
        honeypot_ports = honeypot_ports or []
        forward_ports = forward_ports or []
        sandbox_ports = sandbox_ports or []
        
        # Configure honeypots
        for port, service in honeypot_ports:
            config = PortConfig(
                port=port,
                is_honeypot=True,
                real_backend=None,
                sandbox_enabled=False,
                service_banner=f"{service} honeypot"
            )
            self.network_defense.configure_port(config)
        
        # Configure forwarders
        for listen_port, backend_host, backend_port in forward_ports:
            config = PortConfig(
                port=listen_port,
                is_honeypot=False,
                real_backend=(backend_host, backend_port),
                sandbox_enabled=False,
                service_banner="forwarded"
            )
            self.network_defense.configure_port(config)
        
        # Configure sandboxed ports
        for port, service in sandbox_ports:
            config = PortConfig(
                port=port,
                is_honeypot=False,
                real_backend=None,
                sandbox_enabled=True,
                service_banner=f"{service} sandboxed"
            )
            self.network_defense.configure_port(config)
        
        # Create default sandbox
        if sandbox_ports:
            self.network_defense.create_sandbox("main-sandbox")
        
        print(f"Network defense configured:")
        print(f"  Honeypots: {len(honeypot_ports)}")
        print(f"  Forwarders: {len(forward_ports)}")
        print(f"  Sandboxes: {len(sandbox_ports)}")
    
    def start_network_defense(self):
        """Start network defense (requires proper permissions)"""
        if not self.config.get('enable_network_defense'):
            print("Network defense disabled in config")
            return
        
        print("Starting network defense listeners...")
        threads = self.network_defense.start()
        print(f"Started {len(threads)} listener threads")
        return threads
    
    def stop_network_defense(self):
        """Stop network defense"""
        self.network_defense.stop()
        print("Network defense stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "timestamp": datetime.now().isoformat(),
            "crypto_engine": {
                "mutation_history": len(self.crypto_engine.mutation_history),
                "last_mutations": self.crypto_engine.mutation_history[-5:] 
                                 if self.crypto_engine.mutation_history else []
            },
            "ai_orchestrator": {
                "vectors_in_memory": len(self.ai_orchestrator.vector_db.vectors),
                "decisions_made": len(self.ai_orchestrator.decision_history),
                "recent_decisions": self.ai_orchestrator.get_decision_history(3)
            },
            "network_defense": self.network_defense.get_status_report(),
            "operations": {
                "total": len(self.operation_log),
                "recent": self.operation_log[-5:]
            }
        }
    
    def _log_operation(self, op_type: str, details: Dict):
        """Log system operation"""
        self.operation_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": op_type,
            "details": details
        })
    
    def train_from_repository_patterns(self, repo_paths: list):
        """
        Analyze ML/crypto algorithms from repositories and learn patterns
        This would integrate with the cloned repos
        """
        print("Training AI from repository patterns...")
        
        # Placeholder for actual repo analysis
        # In production, this would:
        # 1. Scan algorithm implementations
        # 2. Extract crypto patterns
        # 3. Learn optimal cipher combinations
        # 4. Build attack pattern database
        
        training_data = [
            ("Complex mathematical operations benefit from performance-optimized ciphers",
             {"category": "optimization", "source": "ml_algorithms"}),
            ("NLP data often contains PII requiring high-security encryption",
             {"category": "sensitivity", "source": "nlp_algorithms"}),
            ("Network attack patterns from RAT analysis inform defense strategies",
             {"category": "defense", "source": "security_research"}),
        ]
        
        for content, metadata in training_data:
            self.ai_orchestrator.vector_db.add(content, metadata)
        
        print(f"  ✓ Added {len(training_data)} training patterns")
    
    def export_audit_report(self, filepath: str):
        """Export comprehensive audit report"""
        report = {
            "system_info": {
                "generated": datetime.now().isoformat(),
                "version": "1.0.0",
                "config": self.config
            },
            "status": self.get_system_status(),
            "operation_log": self.operation_log
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Audit report exported to: {filepath}")


def main():
    """Main demo/test function"""
    print("=" * 60)
    print("QUANTUM-ADAPTIVE CRYPTO ORCHESTRATOR")
    print("=" * 60)
    print()
    
    if not MODULES_AVAILABLE:
        print("ERROR: Core modules not available")
        print("Make sure crypto_engine, ai_orchestrator, and network_security")
        print("modules are in the correct locations")
        return
    
    # Initialize system
    system = QuantumAdaptiveSystem()
    
    # Test 1: Adaptive encryption with different scenarios
    print("\n" + "=" * 60)
    print("TEST 1: Adaptive Encryption Scenarios")
    print("=" * 60)
    
    # Scenario A: High-security data
    print("\n[Scenario A: Top Secret Document]")
    plaintext_a = b"TOP SECRET: Nuclear launch codes and strategic defense systems"
    encrypted_a = system.adaptive_encrypt(
        plaintext_a,
        sensitivity=10,
        performance_priority=2,
        threat_context={'threat_level': 9}
    )
    print(f"Cipher chain: {encrypted_a['metadata'].cipher_chain}")
    print(f"Manchester layers: {encrypted_a['metadata'].manchester_layers}")
    print(f"Time: {encrypted_a['encryption_time']:.4f}s")
    
    # Scenario B: Performance-critical data
    print("\n[Scenario B: Real-time Sensor Data]")
    plaintext_b = b"Sensor readings: temp=72.3F, humidity=45%, pressure=1013hPa" * 10
    encrypted_b = system.adaptive_encrypt(
        plaintext_b,
        sensitivity=3,
        performance_priority=10,
        threat_context={'threat_level': 2}
    )
    print(f"Cipher chain: {encrypted_b['metadata'].cipher_chain}")
    print(f"Manchester layers: {encrypted_b['metadata'].manchester_layers}")
    print(f"Time: {encrypted_b['encryption_time']:.4f}s")
    
    # Test decryption
    print("\n[Verifying Decryption]")
    decrypted_a = system.adaptive_decrypt(encrypted_a)
    decrypted_b = system.adaptive_decrypt(encrypted_b)
    print(f"Scenario A match: {plaintext_a == decrypted_a}")
    print(f"Scenario B match: {plaintext_b == decrypted_b}")
    
    # Test 2: Network defense configuration
    print("\n" + "=" * 60)
    print("TEST 2: Network Defense Configuration")
    print("=" * 60)
    
    system.configure_network_defense(
        honeypot_ports=[(2222, "SSH"), (8080, "HTTP")],
        sandbox_ports=[(3306, "MySQL")]
    )
    
    # Test 3: AI learning
    print("\n" + "=" * 60)
    print("TEST 3: AI Learning from Operations")
    print("=" * 60)
    
    system.train_from_repository_patterns([])
    
    # Simulate attack learning
    system.ai_orchestrator.learn_from_attack(
        "port_scan",
        "detected_and_blocked",
        {"source": "192.168.1.100", "ports_scanned": 50}
    )
    
    # Test 4: System status report
    print("\n" + "=" * 60)
    print("TEST 4: System Status Report")
    print("=" * 60)
    
    status = system.get_system_status()
    print(f"\nCrypto mutations: {status['crypto_engine']['mutation_history']}")
    print(f"AI vectors: {status['ai_orchestrator']['vectors_in_memory']}")
    print(f"AI decisions: {status['ai_orchestrator']['decisions_made']}")
    print(f"Total operations: {status['operations']['total']}")
    
    # Test 5: Export audit report
    print("\n" + "=" * 60)
    print("TEST 5: Audit Report Export")
    print("=" * 60)
    
    report_path = "/tmp/qac_audit_report.json"
    system.export_audit_report(report_path)
    
    # Final summary
    print("\n" + "=" * 60)
    print("DEMO COMPLETE - System Ready for Production")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Clone repositories to ai_resources/ directories")
    print("  2. Install: pip install pycryptodome numpy --break-system-packages")
    print("  3. Configure network defense ports (requires sudo for privileged ports)")
    print("  4. Start system.start_network_defense() for active protection")
    print("  5. Integrate with your GhostGoatNode and ADAP systems")


if __name__ == "__main__":
    main()
