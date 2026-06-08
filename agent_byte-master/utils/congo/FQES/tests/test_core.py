"""
Test suite for FQES core functionality
"""

import unittest
from src.core.fractal_encoder import FractalEncoder, ManchesterEncoder, LatticeCrypto

class TestFractalEncoder(unittest.TestCase):
    
    def setUp(self):
        self.encoder = FractalEncoder()
        self.sample_data = b"Test data for fractal compression" * 100
    
    def test_compression_with_proof(self):
        compressed, proof = self.encoder.compress_with_proof(self.sample_data)
        self.assertLess(len(compressed), len(self.sample_data))
        self.assertIsInstance(proof, str)
        self.assertEqual(len(proof), 128)  # Whirlpool hash length
    
    def test_integrity_verification(self):
        compressed, proof = self.encoder.compress_with_proof(self.sample_data)
        verified = self.encoder.verify_integrity(self.sample_data, compressed, proof)
        self.assertTrue(verified)

class TestManchesterEncoder(unittest.TestCase):
    
    def test_encoding_decoding(self):
        encoder = ManchesterEncoder()
        original = b"Test data"
        encoded = encoder.encode(original)
        decoded = encoder.decode(encoded)
        self.assertEqual(original, decoded)

class TestLatticeCrypto(unittest.TestCase):
    
    def test_key_generation(self):
        crypto = LatticeCrypto()
        public, private = crypto.generate_keypair()
        self.assertIsInstance(public, bytes)
        self.assertIsInstance(private, bytes)
    
    def test_encryption_decryption(self):
        crypto = LatticeCrypto()
        public, private = crypto.generate_keypair()
        data = b"Secret message"
        encrypted = crypto.encrypt(data, public)
        decrypted = crypto.decrypt(encrypted, private)
        self.assertEqual(data, decrypted)

if __name__ == '__main__':
    unittest.main()
