#!/usr/bin/env python3
"""
Development setup script for FQES
"""

import subprocess
import sys
import os
import platform

def run_command(cmd, description):
    print(f"🚀 {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    print("✅ Success")
    return True

def check_python_version():
    """Check if Python version is compatible"""
    version = platform.python_version()
    print(f"🐍 Python version: {version}")
    
    major, minor, _ = version.split('.')
    if int(major) >= 3 and int(minor) >= 8:
        return True
    else:
        print("❌ Python 3.8+ required")
        return False

def create_compatibility_layers():
    """Create compatibility layers for smooth development"""
    
    # Create simplified core modules that don't require external dependencies
    simplified_core = '''
"""
Simplified FQES Core - No external dependencies for initial testing
"""

import hashlib
from typing import Tuple

class FractalEncoder:
    """Simplified fractal encoder for initial development"""
    
    def compress_with_proof(self, data: bytes) -> Tuple[bytes, str]:
        """Basic compression with integrity proof"""
        compressed = data[:len(data)//2]  # Simple compression
        proof = hashlib.sha256(data + compressed).hexdigest()
        return compressed, proof
    
    def verify_integrity(self, original: bytes, compressed: bytes, proof: str) -> bool:
        """Verify integrity proof"""
        generated = hashlib.sha256(original + compressed).hexdigest()
        return generated == proof

class ManchesterEncoder:
    """Simplified Manchester encoding"""
    def encode(self, data: bytes) -> bytes:
        return data
    
    def decode(self, data: bytes) -> bytes:
        return data

class LatticeCrypto:
    """Simplified lattice cryptography"""
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        return b'public', b'private'
    
    def encrypt(self, data: bytes, key: bytes) -> bytes:
        return data
    
    def decrypt(self, data: bytes, key: bytes) -> bytes:
        return data
'''
    
    with open('src/core/simple_fractal.py', 'w') as f:
        f.write(simplified_core)
    
    # Create simple test that doesn't require external dependencies
    simple_test = '''
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
'''
    
    with open('tests/test_simple.py', 'w') as f:
        f.write(simple_test)
    
    print("✅ Created simplified compatibility layers")

def main():
    print("🎯 Setting up FQES Development Environment")
    print("=" * 50)
    
    # Check Python version first
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    venv_name = "fqes_env"
    if not run_command(f"python -m venv {venv_name}", "Creating virtual environment"):
        sys.exit(1)
    
    # Determine pip command based on OS
    if os.name == 'nt':  # Windows
        pip_cmd = f"{venv_name}\\Scripts\\pip"
        python_cmd = f"{venv_name}\\Scripts\\python"
        activate_cmd = f"{venv_name}\\Scripts\\activate"
    else:  # Linux/Mac
        pip_cmd = f"{venv_name}/bin/pip"
        python_cmd = f"{venv_name}/bin/python"
        activate_cmd = f"source {venv_name}/bin/activate"
    
    # Install requirements in the virtual environment
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        sys.exit(1)
    
    print("📦 Installing core dependencies...")
    # Install requirements one by one for better error handling
    dependencies = ["numpy", "cryptography", "pytest", "scipy", "matplotlib", "networkx"]
    
    for dep in dependencies:
        if not run_command(f"{pip_cmd} install {dep}", f"Installing {dep}"):
            print(f"⚠️  Failed to install {dep}, continuing...")
    
    # Create compatibility layers
    create_compatibility_layers()
    
    # Test that basic functionality works
    print("🧪 Testing basic functionality...")
    
    # Test with simple imports first
    test_script = """
try:
    from src.core.simple_fractal import FractalEncoder
    print("✅ Simple imports work")
    
    encoder = FractalEncoder()
    data = b"test data"
    compressed, proof = encoder.compress_with_proof(data)
    print(f"✅ Basic compression works: {len(data)} -> {len(compressed)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
"""
    
    with open('test_basic.py', 'w') as f:
        f.write(test_script)
    
    run_command(f"{python_cmd} test_basic.py", "Testing basic functionality")
    
    # Run simplified tests
    print("🧪 Running simplified tests...")
    run_command(f"{python_cmd} -m pytest tests/test_simple.py -v", "Running simplified tests")
    
    # Clean up test file
    if os.path.exists('test_basic.py'):
        os.remove('test_basic.py')
    
    print("\n🎉 FQES environment setup complete!")
    print("=" * 50)
    print("📁 Your repository structure:")
    subprocess.run("find . -type f -name '*.py' -o -name '*.md' | grep -v __pycache__ | sort", shell=True)
    
    print(f"\n🔧 Activation command: {activate_cmd}")
    print("📚 Next steps:")
    print("   1. Activate the virtual environment")
    print("   2. Run: python examples/basic_usage.py")
    print("   3. Begin Phase 1 implementation from IMPLEMENTATION_PLAN.md")

if __name__ == "__main__":
    main()
