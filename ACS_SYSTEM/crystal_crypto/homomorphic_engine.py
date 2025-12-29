# FILE: cipherdsl/homomorphic_engine.py

import os
import tenseal as ts # Assuming you chose the tenseal/SEAL backend
from typing import List, Tuple

# --- Tenseal/SEAL Context and Keys ---
# The context defines the encryption parameters (e.g., polynomial modulus, scaling factor)
# This context must be saved and loaded across sessions.

class HomomorphicEngine:
    """
    Manages the HE context, keys, and operations (addition, multiplication)
    on encrypted data using a lattice-based scheme (e.g., SEAL).
    """
    
    def __init__(self, key_path: str = "keys/he_context.bin"):
        self.key_path = key_path
        self.context = None
        
    def setup_context(self, poly_modulus_degree: int = 4096, coeff_modulus_bits: List[int] = [40, 20, 40]):
        """
        Generates or loads the HE context and keys.
        """
        if os.path.exists(self.key_path):
            # Load existing context and keys
            print(f"[HE] Loading context from {self.key_path}")
            self.context = ts.context_from(ts.scheme_type.BFV, self.key_path)
        else:
            # Generate new context (using BFV scheme)
            print("[HE] Generating new context and keys...")
            self.context = ts.context(
                ts.scheme_type.BFV,
                poly_modulus_degree=poly_modulus_degree,
                coeff_modulus_bits=coeff_modulus_bits
            )
            self.context.generate_galois_keys()
            self.context.generate_relin_keys()
            
            # Save the context (required for key-sharing)
            # In a real system, the public keys are shared, not the whole context
            self.context.save(self.key_path)
        
        # Set the encryption key (private key for decryption)
        # Note: The context holds public keys for encryption and evaluation.
        # The Secret Key (sk) is stored securely and is only for decryption.
        self.sk = self.context.secret_key()
        
    def encrypt_data(self, plaintext: List[int]) -> ts.CKKSEncoder:
        """Encrypts a list of integers."""
        if not self.context: self.setup_context()
        print(f"[HE] Encrypting {len(plaintext)} values...")
        # Use BFV for integer operations
        return ts.bfv_vector(self.context, plaintext)

    def decrypt_data(self, ciphertext: ts.CKKSEncoder) -> List[int]:
        """Decrypts a ciphertext vector."""
        return ciphertext.decrypt()

    def add_ciphertexts(self, cipher_a: ts.CKKSEncoder, cipher_b: ts.CKKSEncoder) -> ts.CKKSEncoder:
        """Homomorphic addition (Ciphertext + Ciphertext)."""
        print("[HE] Performing Homomorphic Addition...")
        return cipher_a + cipher_b

    def serialize_ciphertext(self, ciphertext: ts.CKKSEncoder) -> bytes:
        """Converts ciphertext object to transportable bytes."""
        return ciphertext.serialize()

    def deserialize_ciphertext(self, cipher_bytes: bytes) -> ts.CKKSEncoder:
        """Converts bytes back to a ciphertext object."""
        return ts.BFVVector.load(self.context, cipher_bytes)


