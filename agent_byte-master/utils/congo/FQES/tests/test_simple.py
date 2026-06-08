
"""
Simplified tests that work without external dependencies
"""

import unittest
from src.core.simple_fractal import FractalEncoder, ManchesterEncoder, LatticeCrypto

class TestSimpleFractal(unittest.TestCase):
    
    def setUp(self):
        self.encoder = FractalEncoder()
        self.sample_data = b"Test data" * 100
    
    def test_basic_compression(self):
        compressed, proof = self.encoder.compress_with_proof(self.sample_data)
        self.assertLess(len(compressed), len(self.sample_data))
        self.assertIsInstance(proof, str)
    
    def test_integrity_verification(self):
        compressed, proof = self.encoder.compress_with_proof(self.sample_data)
        verified = self.encoder.verify_integrity(self.sample_data, compressed, proof)
        self.assertTrue(verified)

if __name__ == '__main__':
    unittest.main()
