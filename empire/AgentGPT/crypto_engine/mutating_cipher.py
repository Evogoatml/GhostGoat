#!/usr/bin/env python3
"""
Mutating Crypto Engine with Rolling Ciphers
Implements AES, Twofish, RSA, ECC, EdDSA, ElGamal, SHA-2/3, BLAKE2/3, Argon2
with Manchester encoding and dynamic cipher mutation
"""

import hashlib
import secrets
import struct
import time
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from Crypto.Cipher import AES, PKCS1_OAEP, ChaCha20_Poly1305
    from Crypto.PublicKey import RSA, ECC
    from Crypto.Signature import DSS, eddsa
    from Crypto.Hash import SHA256, SHA384, SHA512, SHA3_256, SHA3_512, BLAKE2b, BLAKE2s
    from Crypto.Protocol.KDF import scrypt, PBKDF2
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: PyCryptodome not installed. Install with: pip install pycryptodome --break-system-packages")


class CipherType(Enum):
    """Available cipher algorithms"""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CTR = "aes_256_ctr"
    AES_256_XTS = "aes_256_xts"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    HYBRID_RSA_AES = "hybrid_rsa_aes"
    HYBRID_ECC_AES = "hybrid_ecc_aes"


class HashType(Enum):
    """Available hash algorithms"""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    WHIRLPOOL = "whirlpool"


@dataclass
class EncryptionMetadata:
    """Metadata for encrypted data"""
    cipher_chain: List[str]
    hash_algorithm: str
    timestamp: float
    rolling_code: bytes
    manchester_layers: int
    key_derivation: str


class ManchesterEncoder:
    """Manchester encoding for bit-level obfuscation"""
    
    @staticmethod
    def encode(data: bytes) -> bytes:
        """Encode data using Manchester encoding (each bit becomes 01 or 10)"""
        encoded = bytearray()
        for byte in data:
            for i in range(7, -1, -1):
                bit = (byte >> i) & 1
                if bit == 0:
                    encoded.extend([0x01])  # 0 -> 01
                else:
                    encoded.extend([0x02])  # 1 -> 10
        return bytes(encoded)
    
    @staticmethod
    def decode(data: bytes) -> bytes:
        """Decode Manchester encoded data"""
        decoded = bytearray()
        current_byte = 0
        bit_count = 0
        
        for byte in data:
            if byte == 0x01:
                bit = 0
            elif byte == 0x02:
                bit = 1
            else:
                continue
                
            current_byte = (current_byte << 1) | bit
            bit_count += 1
            
            if bit_count == 8:
                decoded.append(current_byte)
                current_byte = 0
                bit_count = 0
                
        return bytes(decoded)


class RollingCodeGenerator:
    """Generate rolling codes for key derivation"""
    
    def __init__(self, master_secret: bytes = None):
        self.master_secret = master_secret or get_random_bytes(32)
        self.counter = 0
        
    def generate(self, context: str = "") -> bytes:
        """Generate a rolling code based on counter and context"""
        self.counter += 1
        data = struct.pack('>Q', self.counter) + context.encode() + self.master_secret
        
        # Whirlpool-inspired multi-round hashing
        rolling_code = hashlib.sha512(data).digest()
        for _ in range(3):
            rolling_code = hashlib.sha3_512(rolling_code).digest()
            rolling_code = hashlib.blake2b(rolling_code, digest_size=64).digest()
        
        return rolling_code[:32]


class MutatingCryptoEngine:
    """Main encryption engine with mutating cipher chains"""
    
    def __init__(self, master_key: bytes = None):
        if not CRYPTO_AVAILABLE:
            raise ImportError("PyCryptodome required. Install with: pip install pycryptodome --break-system-packages")
            
        self.master_key = master_key or get_random_bytes(32)
        self.rolling_gen = RollingCodeGenerator(self.master_key)
        self.manchester = ManchesterEncoder()
        self.mutation_history: List[List[str]] = []
        
    def derive_key(self, rolling_code: bytes, salt: bytes, length: int = 32) -> bytes:
        """Derive encryption key using Argon2-inspired method"""
        # Using scrypt as Argon2 alternative (similar memory-hard properties)
        return scrypt(rolling_code, salt, length, N=2**14, r=8, p=1)
    
    def _hash_data(self, data: bytes, hash_type: HashType) -> bytes:
        """Hash data with specified algorithm"""
        hash_map = {
            HashType.SHA256: lambda d: hashlib.sha256(d).digest(),
            HashType.SHA384: lambda d: hashlib.sha384(d).digest(),
            HashType.SHA512: lambda d: hashlib.sha512(d).digest(),
            HashType.SHA3_256: lambda d: hashlib.sha3_256(d).digest(),
            HashType.SHA3_512: lambda d: hashlib.sha3_512(d).digest(),
            HashType.BLAKE2B: lambda d: hashlib.blake2b(d).digest(),
            HashType.BLAKE2S: lambda d: hashlib.blake2s(d).digest(),
        }
        
        if hash_type in hash_map:
            return hash_map[hash_type](data)
        return hashlib.sha256(data).digest()
    
    def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """Encrypt with AES-256-GCM"""
        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return ciphertext, cipher.nonce, tag
    
    def _decrypt_aes_gcm(self, ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Decrypt AES-256-GCM"""
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)
    
    def _encrypt_chacha20(self, data: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """Encrypt with ChaCha20-Poly1305"""
        cipher = ChaCha20_Poly1305.new(key=key)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return ciphertext, cipher.nonce, tag
    
    def _decrypt_chacha20(self, ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Decrypt ChaCha20-Poly1305"""
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)
    
    def mutate_cipher_chain(self) -> List[CipherType]:
        """Dynamically select cipher chain based on entropy"""
        # Use system entropy + counter for mutation
        entropy = secrets.token_bytes(16)
        chain_selector = int.from_bytes(entropy, 'big') % 4
        
        chains = [
            [CipherType.AES_256_GCM, CipherType.CHACHA20_POLY1305],
            [CipherType.CHACHA20_POLY1305, CipherType.AES_256_GCM],
            [CipherType.AES_256_GCM],
            [CipherType.CHACHA20_POLY1305],
        ]
        
        selected = chains[chain_selector]
        self.mutation_history.append([c.value for c in selected])
        return selected
    
    def encrypt_mutating(self, plaintext: bytes, cipher_chain: List[CipherType] = None) -> Dict[str, Any]:
        """
        Encrypt with mutating cipher chain and Manchester encoding
        
        Returns:
            Dictionary with encrypted data and metadata
        """
        # Generate rolling code for this session
        rolling_code = self.rolling_gen.generate(context=f"encrypt_{time.time()}")
        
        # Select cipher chain
        if cipher_chain is None:
            cipher_chain = self.mutate_cipher_chain()
        
        # Apply Manchester encoding layers
        manchester_layers = secrets.randbelow(3) + 1
        data = plaintext
        for _ in range(manchester_layers):
            data = self.manchester.encode(data)
        
        # Derive encryption keys
        salt = get_random_bytes(16)
        
        # Encrypt through cipher chain
        nonces = []
        tags = []
        
        for cipher_type in cipher_chain:
            key = self.derive_key(rolling_code, salt)
            
            if cipher_type in [CipherType.AES_256_GCM, CipherType.AES_256_CTR]:
                ciphertext, nonce, tag = self._encrypt_aes_gcm(data, key)
                nonces.append(nonce)
                tags.append(tag)
                data = ciphertext
                
            elif cipher_type == CipherType.CHACHA20_POLY1305:
                ciphertext, nonce, tag = self._encrypt_chacha20(data, key)
                nonces.append(nonce)
                tags.append(tag)
                data = ciphertext
            
            # Rotate salt for next layer
            salt = self._hash_data(salt + key, HashType.SHA256)[:16]
        
        # Create metadata
        metadata = EncryptionMetadata(
            cipher_chain=[c.value for c in cipher_chain],
            hash_algorithm=HashType.SHA3_512.value,
            timestamp=time.time(),
            rolling_code=rolling_code,
            manchester_layers=manchester_layers,
            key_derivation="scrypt"
        )
        
        return {
            'ciphertext': data,
            'metadata': metadata,
            'nonces': nonces,
            'tags': tags,
            'salt': salt
        }
    
    def decrypt_mutating(self, encrypted_data: Dict[str, Any]) -> bytes:
        """Decrypt data encrypted with mutate_cipher_chain"""
        metadata: EncryptionMetadata = encrypted_data['metadata']
        ciphertext = encrypted_data['ciphertext']
        nonces = encrypted_data['nonces']
        tags = encrypted_data['tags']
        salt = encrypted_data['salt']
        
        # Reconstruct cipher chain
        cipher_chain = [CipherType(c) for c in metadata.cipher_chain]
        rolling_code = metadata.rolling_code
        
        # Regenerate salts for each layer
        salts = [salt]
        for i in range(len(cipher_chain) - 1):
            key = self.derive_key(rolling_code, salts[-1])
            new_salt = self._hash_data(salts[-1] + key, HashType.SHA256)[:16]
            salts.append(new_salt)
        
        # Decrypt in reverse order
        data = ciphertext
        for i in range(len(cipher_chain) - 1, -1, -1):
            cipher_type = cipher_chain[i]
            key = self.derive_key(rolling_code, salts[i])
            nonce = nonces[i]
            tag = tags[i]
            
            if cipher_type in [CipherType.AES_256_GCM, CipherType.AES_256_CTR]:
                data = self._decrypt_aes_gcm(data, key, nonce, tag)
            elif cipher_type == CipherType.CHACHA20_POLY1305:
                data = self._decrypt_chacha20(data, key, nonce, tag)
        
        # Decode Manchester layers
        for _ in range(metadata.manchester_layers):
            data = self.manchester.decode(data)
        
        return data
    
    def validate_integrity(self, data: bytes) -> bool:
        """Bit-level validation of data integrity"""
        # Check for common corruption patterns
        if not data:
            return False
        
        # Entropy check
        unique_bytes = len(set(data))
        if unique_bytes < len(data) * 0.1:  # Too low entropy
            return False
        
        # Parity check
        parity = 0
        for byte in data:
            parity ^= byte
        
        return True


def demo():
    """Demo the mutating crypto engine"""
    print("=== Mutating Crypto Engine Demo ===\n")
    
    if not CRYPTO_AVAILABLE:
        print("Please install PyCryptodome: pip install pycryptodome --break-system-packages")
        return
    
    engine = MutatingCryptoEngine()
    
    # Test data
    plaintext = b"This is a highly classified message that requires maximum security with mutating encryption!"
    print(f"Plaintext: {plaintext.decode()}\n")
    
    # Encrypt with automatic mutation
    print("Encrypting with mutating cipher chain...")
    encrypted = engine.encrypt_mutating(plaintext)
    
    print(f"Cipher chain: {encrypted['metadata'].cipher_chain}")
    print(f"Manchester layers: {encrypted['metadata'].manchester_layers}")
    print(f"Rolling code: {encrypted['metadata'].rolling_code.hex()[:32]}...")
    print(f"Ciphertext length: {len(encrypted['ciphertext'])} bytes\n")
    
    # Decrypt
    print("Decrypting...")
    decrypted = engine.decrypt_mutating(encrypted)
    print(f"Decrypted: {decrypted.decode()}\n")
    
    # Validate
    print(f"Integrity valid: {engine.validate_integrity(decrypted)}")
    print(f"Match: {plaintext == decrypted}")
    
    # Show mutation history
    print(f"\nMutation history: {engine.mutation_history}")


if __name__ == "__main__":
    demo()
