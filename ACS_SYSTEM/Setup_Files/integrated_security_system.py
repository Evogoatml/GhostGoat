#!/usr/bin/env python3
"""
Integrated Cybersecurity System
Combines crystal lattice homomorphic encryption, bit manipulation ciphers,
automated auditing, and comprehensive security monitoring
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import secrets

# Import our custom crypto modules
import sys
sys.path.append('/home/claude/crypto')

from homomorphic_crystal import (
    HomomorphicCrypto, GraphHomomorphicEncryption,
    PublicKey, PrivateKey, Ciphertext
)
from bit_cipher import BitCipher, StreamCipher, BitManipulationEncoder


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegratedSecuritySystem:
    """
    Complete security system integrating multiple cryptographic
    and auditing capabilities
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize integrated security system
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        
        # Initialize cryptographic systems
        self.homomorphic_crypto = HomomorphicCrypto(
            dimension=self.config.get('lattice_dimension', 1024),
            security_level=self.config.get('security_level', 128)
        )
        
        # Generate master keys
        self.master_key = secrets.token_bytes(32)
        self.block_cipher = BitCipher(self.master_key, rounds=16)
        self.stream_cipher = StreamCipher(self.master_key)
        
        # Initialize key storage
        self.keys = {
            'homomorphic': {},
            'symmetric': {},
            'sessions': {}
        }
        
        # Security event log
        self.event_log = []
        
        logger.info("Integrated Security System initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'lattice_dimension': 1024,
            'security_level': 128,
            'encryption_algorithm': 'homomorphic',
            'audit_enabled': True,
            'logging_level': 'INFO',
            'key_rotation_days': 90,
            'session_timeout_minutes': 30
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def generate_user_keys(self, user_id: str) -> Dict[str, Any]:
        """
        Generate complete key set for a user
        Includes homomorphic and symmetric keys
        """
        logger.info(f"Generating keys for user: {user_id}")
        
        # Generate homomorphic keypair
        public_key, private_key = self.homomorphic_crypto.generate_keypair()
        
        # Generate symmetric key for this user
        symmetric_key = secrets.token_bytes(32)
        
        # Store keys
        self.keys['homomorphic'][user_id] = {
            'public': public_key,
            'private': private_key,
            'created': datetime.now().isoformat()
        }
        
        self.keys['symmetric'][user_id] = {
            'key': symmetric_key,
            'created': datetime.now().isoformat()
        }
        
        # Log event
        self._log_security_event('KEY_GENERATION', {
            'user_id': user_id,
            'key_types': ['homomorphic', 'symmetric']
        })
        
        return {
            'user_id': user_id,
            'public_key': public_key.to_dict(),
            'symmetric_key': symmetric_key.hex(),
            'created': datetime.now().isoformat()
        }
    
    def encrypt_data(self, data: bytes, user_id: str, 
                    method: str = 'homomorphic') -> Dict[str, Any]:
        """
        Encrypt data using specified method
        
        Args:
            data: Data to encrypt
            user_id: User identifier
            method: 'homomorphic', 'block', or 'stream'
        
        Returns:
            Encrypted data with metadata
        """
        logger.info(f"Encrypting data for {user_id} using {method}")
        
        timestamp = datetime.now().isoformat()
        
        if method == 'homomorphic':
            if user_id not in self.keys['homomorphic']:
                raise ValueError(f"No keys found for user {user_id}")
            
            public_key = self.keys['homomorphic'][user_id]['public']
            ciphertext = self.homomorphic_crypto.encrypt(public_key, data)
            
            encrypted_data = {
                'method': 'homomorphic',
                'ciphertext': ciphertext.to_dict(),
                'user_id': user_id,
                'timestamp': timestamp,
                'data_length': len(data)
            }
        
        elif method == 'block':
            if user_id not in self.keys['symmetric']:
                raise ValueError(f"No symmetric key for user {user_id}")
            
            key = self.keys['symmetric'][user_id]['key']
            cipher = BitCipher(key, rounds=16)
            ciphertext = cipher.encrypt(data)
            
            encrypted_data = {
                'method': 'block',
                'ciphertext': ciphertext.hex(),
                'user_id': user_id,
                'timestamp': timestamp,
                'data_length': len(data)
            }
        
        elif method == 'stream':
            if user_id not in self.keys['symmetric']:
                raise ValueError(f"No symmetric key for user {user_id}")
            
            key = self.keys['symmetric'][user_id]['key']
            cipher = StreamCipher(key)
            ciphertext = cipher.encrypt(data)
            
            encrypted_data = {
                'method': 'stream',
                'ciphertext': ciphertext.hex(),
                'user_id': user_id,
                'timestamp': timestamp,
                'data_length': len(data)
            }
        
        else:
            raise ValueError(f"Unknown encryption method: {method}")
        
        # Log encryption event
        self._log_security_event('DATA_ENCRYPTED', {
            'user_id': user_id,
            'method': method,
            'data_length': len(data)
        })
        
        return encrypted_data
    
    def decrypt_data(self, encrypted_data: Dict[str, Any]) -> bytes:
        """
        Decrypt data based on encryption method
        
        Args:
            encrypted_data: Dictionary containing encrypted data and metadata
        
        Returns:
            Decrypted plaintext
        """
        method = encrypted_data['method']
        user_id = encrypted_data['user_id']
        
        logger.info(f"Decrypting data for {user_id} using {method}")
        
        if method == 'homomorphic':
            if user_id not in self.keys['homomorphic']:
                raise ValueError(f"No keys found for user {user_id}")
            
            private_key = self.keys['homomorphic'][user_id]['private']
            ciphertext = Ciphertext.from_dict(encrypted_data['ciphertext'])
            data_length = encrypted_data['data_length']
            
            plaintext = self.homomorphic_crypto.decrypt(
                private_key, ciphertext, data_length
            )
        
        elif method == 'block':
            if user_id not in self.keys['symmetric']:
                raise ValueError(f"No symmetric key for user {user_id}")
            
            key = self.keys['symmetric'][user_id]['key']
            cipher = BitCipher(key, rounds=16)
            ciphertext = bytes.fromhex(encrypted_data['ciphertext'])
            
            plaintext = cipher.decrypt(ciphertext)
        
        elif method == 'stream':
            if user_id not in self.keys['symmetric']:
                raise ValueError(f"No symmetric key for user {user_id}")
            
            key = self.keys['symmetric'][user_id]['key']
            cipher = StreamCipher(key)
            ciphertext = bytes.fromhex(encrypted_data['ciphertext'])
            
            plaintext = cipher.decrypt(ciphertext)
        
        else:
            raise ValueError(f"Unknown encryption method: {method}")
        
        # Log decryption event
        self._log_security_event('DATA_DECRYPTED', {
            'user_id': user_id,
            'method': method
        })
        
        return plaintext
    
    def homomorphic_compute(self, encrypted_data1: Dict[str, Any],
                          encrypted_data2: Dict[str, Any],
                          operation: str = 'add') -> Dict[str, Any]:
        """
        Perform computation on encrypted data without decryption
        
        Args:
            encrypted_data1: First encrypted operand
            encrypted_data2: Second encrypted operand
            operation: 'add' or 'xor'
        
        Returns:
            Result of computation (still encrypted)
        """
        if encrypted_data1['method'] != 'homomorphic':
            raise ValueError("Operation requires homomorphic encryption")
        
        ct1 = Ciphertext.from_dict(encrypted_data1['ciphertext'])
        ct2 = Ciphertext.from_dict(encrypted_data2['ciphertext'])
        
        if operation == 'add':
            result_ct = self.homomorphic_crypto.homomorphic_add(ct1, ct2)
        elif operation == 'xor':
            result_ct = self.homomorphic_crypto.homomorphic_xor(ct1, ct2)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Log computation
        self._log_security_event('HOMOMORPHIC_COMPUTE', {
            'operation': operation,
            'user_id': encrypted_data1['user_id']
        })
        
        return {
            'method': 'homomorphic',
            'ciphertext': result_ct.to_dict(),
            'user_id': encrypted_data1['user_id'],
            'timestamp': datetime.now().isoformat(),
            'operation': operation
        }
    
    def apply_encoding(self, data: bytes, encoding: str = 'gray') -> bytes:
        """
        Apply bit manipulation encoding
        
        Args:
            data: Input data
            encoding: 'gray', 'reverse', or 'avalanche'
        
        Returns:
            Encoded data
        """
        encoder = BitManipulationEncoder()
        
        if encoding == 'gray':
            return encoder.gray_code_encode(data)
        elif encoding == 'reverse':
            return encoder.bit_reversal(data)
        elif encoding == 'avalanche':
            return encoder.avalanche_hash(data)
        else:
            raise ValueError(f"Unknown encoding: {encoding}")
    
    def create_secure_session(self, user_id: str) -> Dict[str, Any]:
        """
        Create secure session with ephemeral keys
        
        Args:
            user_id: User identifier
        
        Returns:
            Session information
        """
        session_id = secrets.token_urlsafe(32)
        session_key = secrets.token_bytes(32)
        
        session = {
            'session_id': session_id,
            'user_id': user_id,
            'session_key': session_key,
            'created': datetime.now().isoformat(),
            'expires': None  # Set based on config
        }
        
        self.keys['sessions'][session_id] = session
        
        self._log_security_event('SESSION_CREATED', {
            'session_id': session_id,
            'user_id': user_id
        })
        
        return {
            'session_id': session_id,
            'session_key': session_key.hex(),
            'created': session['created']
        }
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event for auditing"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'details': details
        }
        
        self.event_log.append(event)
        logger.info(f"Security event: {event_type} - {details}")
    
    def export_audit_log(self, output_path: str):
        """Export security audit log"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump({
                'exported': datetime.now().isoformat(),
                'total_events': len(self.event_log),
                'events': self.event_log
            }, f, indent=2)
        
        logger.info(f"Audit log exported to {output_file}")
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'lattice_dimension': self.homomorphic_crypto.dimension,
                'security_level': self.homomorphic_crypto.security_level,
                'modulus': int(self.homomorphic_crypto.lattice.q)
            },
            'users': {
                'total': len(self.keys['homomorphic']),
                'with_homomorphic_keys': len(self.keys['homomorphic']),
                'with_symmetric_keys': len(self.keys['symmetric'])
            },
            'sessions': {
                'active': len(self.keys['sessions'])
            },
            'events': {
                'total': len(self.event_log),
                'by_type': self._count_events_by_type()
            }
        }
        
        return report
    
    def _count_events_by_type(self) -> Dict[str, int]:
        """Count events by type"""
        counts = {}
        for event in self.event_log:
            event_type = event['type']
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts


def demonstrate_integrated_system():
    """Demonstrate the complete integrated security system"""
    print("=" * 80)
    print("INTEGRATED CYBERSECURITY SYSTEM DEMONSTRATION")
    print("=" * 80)
    
    # Initialize system
    print("\n[1] Initializing Security System...")
    print("-" * 80)
    system = IntegratedSecuritySystem()
    print("✓ System initialized with crystal lattice encryption")
    print(f"  Lattice Dimension: {system.homomorphic_crypto.dimension}")
    print(f"  Security Level: {system.homomorphic_crypto.security_level} bits")
    print(f"  Modulus: {system.homomorphic_crypto.lattice.q}")
    
    # Generate user keys
    print("\n[2] Generating User Keys...")
    print("-" * 80)
    user1_keys = system.generate_user_keys('user_alice')
    user2_keys = system.generate_user_keys('user_bob')
    print(f"✓ Generated keys for user_alice")
    print(f"✓ Generated keys for user_bob")
    
    # Encrypt data with different methods
    print("\n[3] Encrypting Data with Multiple Methods...")
    print("-" * 80)
    
    message1 = b"Confidential medical records"
    message2 = b"Financial transaction data"
    message3 = b"Real-time sensor stream"
    
    # Homomorphic encryption
    encrypted_homo1 = system.encrypt_data(message1, 'user_alice', 'homomorphic')
    print(f"✓ Encrypted with homomorphic: {message1[:20]}...")
    
    encrypted_homo2 = system.encrypt_data(message2, 'user_alice', 'homomorphic')
    print(f"✓ Encrypted with homomorphic: {message2[:20]}...")
    
    # Block cipher
    encrypted_block = system.encrypt_data(message1, 'user_bob', 'block')
    print(f"✓ Encrypted with block cipher: {message1[:20]}...")
    
    # Stream cipher
    encrypted_stream = system.encrypt_data(message3, 'user_bob', 'stream')
    print(f"✓ Encrypted with stream cipher: {message3[:20]}...")
    
    # Homomorphic computation
    print("\n[4] Performing Homomorphic Computation...")
    print("-" * 80)
    computed_result = system.homomorphic_compute(
        encrypted_homo1, encrypted_homo2, operation='add'
    )
    print("✓ Added two encrypted messages without decryption")
    print("  (Result remains encrypted and can be used in further computations)")
    
    # Decrypt data
    print("\n[5] Decrypting Data...")
    print("-" * 80)
    decrypted1 = system.decrypt_data(encrypted_homo1)
    decrypted2 = system.decrypt_data(encrypted_block)
    decrypted3 = system.decrypt_data(encrypted_stream)
    
    print(f"✓ Decrypted homomorphic: {decrypted1}")
    print(f"✓ Decrypted block:       {decrypted2}")
    print(f"✓ Decrypted stream:      {decrypted3}")
    
    # Test bit manipulation encoding
    print("\n[6] Testing Bit Manipulation Encodings...")
    print("-" * 80)
    test_data = b"TestData123"
    
    gray_encoded = system.apply_encoding(test_data, 'gray')
    print(f"Original:     {test_data.hex()}")
    print(f"Gray encoded: {gray_encoded.hex()}")
    
    avalanche = system.apply_encoding(test_data, 'avalanche')
    print(f"Avalanche:    {avalanche.hex()}")
    
    # Create secure session
    print("\n[7] Creating Secure Session...")
    print("-" * 80)
    session = system.create_secure_session('user_alice')
    print(f"✓ Session created: {session['session_id'][:32]}...")
    
    # Generate security report
    print("\n[8] Generating Security Report...")
    print("-" * 80)
    report = system.generate_security_report()
    print(json.dumps(report, indent=2))
    
    # Export audit log
    print("\n[9] Exporting Audit Log...")
    print("-" * 80)
    system.export_audit_log('/tmp/security_audit.json')
    print("✓ Audit log exported to /tmp/security_audit.json")
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print("\nThe system provides:")
    print("  ✓ Quantum-resistant encryption (lattice-based)")
    print("  ✓ Homomorphic computation on encrypted data")
    print("  ✓ Multiple cipher modes (block, stream)")
    print("  ✓ Advanced bit manipulation encoding")
    print("  ✓ Comprehensive security auditing")
    print("  ✓ Session management")
    print("=" * 80)


if __name__ == '__main__':
    demonstrate_integrated_system()
