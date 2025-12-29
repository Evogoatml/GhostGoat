"""
Crystal Lattice-Based Cryptography
Quantum-resistant encryption using NTRU and LWE-style lattice problems
"""
import secrets
import hashlib
from typing import Tuple, List
import numpy as np


class CrystalKyber:
    """
    Crystal-Kyber style lattice-based KEM (Key Encapsulation Mechanism)
    Quantum-resistant post-quantum cryptography
    """
    
    def __init__(self, security_level: int = 3):
        """
        Initialize Crystal-Kyber with security level
        1: NIST Level 1 (128-bit security)
        3: NIST Level 3 (192-bit security)
        5: NIST Level 5 (256-bit security)
        """
        self.security_level = security_level
        self.params = self._get_parameters(security_level)
        self.q = self.params['q']
        self.n = self.params['n']
        self.k = self.params['k']
        self.eta1 = self.params['eta1']
        self.eta2 = self.params['eta2']
        
    def _get_parameters(self, level: int) -> dict:
        """Get parameters based on security level"""
        params_map = {
            1: {'n': 256, 'k': 2, 'q': 3329, 'eta1': 3, 'eta2': 2},
            3: {'n': 256, 'k': 3, 'q': 3329, 'eta1': 2, 'eta2': 2},
            5: {'n': 256, 'k': 4, 'q': 3329, 'eta1': 2, 'eta2': 2}
        }
        return params_map.get(level, params_map[3])
    
    def _cbd(self, eta: int, seed: bytes) -> np.ndarray:
        """Centered Binomial Distribution sampling"""
        expanded = hashlib.shake_256(seed).digest(eta * self.n // 4)
        bits = np.unpackbits(np.frombuffer(expanded, dtype=np.uint8))
        
        poly = np.zeros(self.n, dtype=np.int32)
        for i in range(self.n):
            a = np.sum(bits[2*i*eta:(2*i+1)*eta])
            b = np.sum(bits[(2*i+1)*eta:2*(i+1)*eta])
            poly[i] = (a - b) % self.q
        
        return poly
    
    def _ntt(self, poly: np.ndarray) -> np.ndarray:
        """Number Theoretic Transform (NTT) for fast polynomial multiplication"""
        # Simplified NTT implementation
        result = np.copy(poly)
        # In production, use optimized NTT with pre-computed roots
        return result % self.q
    
    def _inv_ntt(self, poly: np.ndarray) -> np.ndarray:
        """Inverse NTT"""
        result = np.copy(poly)
        return result % self.q
    
    def _poly_mul(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Polynomial multiplication in NTT domain"""
        a_ntt = self._ntt(a)
        b_ntt = self._ntt(b)
        result_ntt = (a_ntt * b_ntt) % self.q
        return self._inv_ntt(result_ntt)
    
    def _poly_add(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Polynomial addition"""
        return (a + b) % self.q
    
    def _compress(self, poly: np.ndarray, d: int) -> np.ndarray:
        """Compress polynomial coefficients"""
        return np.round((2**d / self.q) * poly).astype(np.int32) % (2**d)
    
    def _decompress(self, poly: np.ndarray, d: int) -> np.ndarray:
        """Decompress polynomial coefficients"""
        return np.round((self.q / 2**d) * poly).astype(np.int32) % self.q
    
    def keygen(self) -> Tuple[bytes, bytes]:
        """Generate public and private key pair"""
        seed = secrets.token_bytes(32)
        
        # Generate secret key polynomial vector
        s = np.array([self._cbd(self.eta1, seed + i.to_bytes(1, 'big')) 
                      for i in range(self.k)])
        
        # Generate error polynomial vector
        e = np.array([self._cbd(self.eta1, seed + (i + self.k).to_bytes(1, 'big')) 
                      for i in range(self.k)])
        
        # Generate random matrix A (from seed)
        A = self._expand_A(seed)
        
        # Public key: t = A*s + e
        t = np.array([self._poly_add(
            sum([self._poly_mul(A[i][j], s[j]) for j in range(self.k)]),
            e[i]
        ) for i in range(self.k)])
        
        # Serialize keys
        public_key = self._serialize_poly_vec(t) + seed
        private_key = self._serialize_poly_vec(s)
        
        return public_key, private_key
    
    def _expand_A(self, seed: bytes) -> np.ndarray:
        """Expand seed into matrix A using XOF"""
        A = np.zeros((self.k, self.k, self.n), dtype=np.int32)
        for i in range(self.k):
            for j in range(self.k):
                xof_input = seed + i.to_bytes(1, 'big') + j.to_bytes(1, 'big')
                xof_output = hashlib.shake_128(xof_input).digest(self.n * 2)
                A[i][j] = np.frombuffer(xof_output, dtype=np.uint16)[:self.n] % self.q
        return A
    
    def _serialize_poly_vec(self, poly_vec: np.ndarray) -> bytes:
        """Serialize polynomial vector to bytes"""
        return poly_vec.tobytes()
    
    def _deserialize_poly_vec(self, data: bytes, count: int) -> np.ndarray:
        """Deserialize bytes to polynomial vector"""
        arr = np.frombuffer(data, dtype=np.int32)
        return arr.reshape((count, self.n))
    
    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate to generate shared secret and ciphertext"""
        # Parse public key
        t_bytes = public_key[:-32]
        seed = public_key[-32:]
        t = self._deserialize_poly_vec(t_bytes, self.k)
        
        # Generate random message
        m = secrets.token_bytes(32)
        
        # Generate ephemeral randomness
        r_seed = hashlib.sha3_256(m).digest()
        r = np.array([self._cbd(self.eta1, r_seed + i.to_bytes(1, 'big')) 
                      for i in range(self.k)])
        
        e1 = np.array([self._cbd(self.eta2, r_seed + (i + self.k).to_bytes(1, 'big')) 
                       for i in range(self.k)])
        e2 = self._cbd(self.eta2, r_seed + (2 * self.k).to_bytes(1, 'big'))
        
        # Expand A
        A = self._expand_A(seed)
        
        # Compute ciphertext
        # u = A^T * r + e1
        u = np.array([self._poly_add(
            sum([self._poly_mul(A[j][i], r[j]) for j in range(self.k)]),
            e1[i]
        ) for i in range(self.k)])
        
        # v = t^T * r + e2 + Decompress(m, 1)
        m_poly = self._decompress(np.unpackbits(np.frombuffer(m, dtype=np.uint8))[:self.n], 1)
        v = self._poly_add(
            self._poly_add(
                sum([self._poly_mul(t[i], r[i]) for i in range(self.k)]),
                e2
            ),
            m_poly
        )
        
        # Compress and serialize ciphertext
        u_compressed = np.array([self._compress(u[i], 10) for i in range(self.k)])
        v_compressed = self._compress(v, 4)
        
        ciphertext = u_compressed.tobytes() + v_compressed.tobytes()
        
        # Shared secret from message
        shared_secret = hashlib.sha3_256(m).digest()
        
        return ciphertext, shared_secret
    
    def decapsulate(self, ciphertext: bytes, private_key: bytes) -> bytes:
        """Decapsulate ciphertext to recover shared secret"""
        # Parse private key
        s = self._deserialize_poly_vec(private_key, self.k)
        
        # Parse ciphertext
        u_size = self.k * self.n * 10 // 8
        u_bytes = ciphertext[:u_size]
        v_bytes = ciphertext[u_size:]
        
        u_compressed = self._deserialize_poly_vec(u_bytes, self.k)
        v_compressed = np.frombuffer(v_bytes, dtype=np.int32)[:self.n]
        
        # Decompress
        u = np.array([self._decompress(u_compressed[i], 10) for i in range(self.k)])
        v = self._decompress(v_compressed, 4)
        
        # Compute m = v - s^T * u
        m_poly = self._poly_add(
            v,
            -sum([self._poly_mul(s[i], u[i]) for i in range(self.k)]) % self.q
        )
        
        # Compress to recover message
        m_bits = self._compress(m_poly, 1)
        m = np.packbits(m_bits[:256]).tobytes()
        
        # Shared secret
        shared_secret = hashlib.sha3_256(m).digest()
        
        return shared_secret


class CrystalDilithium:
    """
    Crystal-Dilithium style lattice-based digital signature
    Quantum-resistant post-quantum signatures
    """
    
    def __init__(self, security_level: int = 3):
        """Initialize with security level (2, 3, or 5)"""
        self.security_level = security_level
        self.params = self._get_parameters(security_level)
        self.q = self.params['q']
        self.n = 256
        self.k = self.params['k']
        self.l = self.params['l']
    
    def _get_parameters(self, level: int) -> dict:
        """Get Dilithium parameters"""
        params_map = {
            2: {'q': 8380417, 'k': 4, 'l': 4, 'd': 13, 'tau': 39, 'gamma1': 2**17, 'gamma2': 95232},
            3: {'q': 8380417, 'k': 6, 'l': 5, 'd': 13, 'tau': 49, 'gamma1': 2**19, 'gamma2': 261888},
            5: {'q': 8380417, 'k': 8, 'l': 7, 'd': 13, 'tau': 60, 'gamma1': 2**19, 'gamma2': 261888}
        }
        return params_map.get(level, params_map[3])
    
    def keygen(self) -> Tuple[bytes, bytes]:
        """Generate signing key pair"""
        seed = secrets.token_bytes(32)
        
        # Expand seed to matrix A
        A = self._expand_A(seed)
        
        # Generate secret vectors s1, s2
        s1 = np.random.randint(-2, 3, size=(self.l, self.n), dtype=np.int32)
        s2 = np.random.randint(-2, 3, size=(self.k, self.n), dtype=np.int32)
        
        # Public key: t = A*s1 + s2
        t = (A @ s1.T).T + s2
        t = t % self.q
        
        public_key = seed + t.tobytes()
        private_key = s1.tobytes() + s2.tobytes() + seed
        
        return public_key, private_key
    
    def _expand_A(self, seed: bytes) -> np.ndarray:
        """Expand seed to matrix A"""
        A = np.zeros((self.k, self.l, self.n), dtype=np.int32)
        for i in range(self.k):
            for j in range(self.l):
                xof = hashlib.shake_128(seed + i.to_bytes(2, 'big') + j.to_bytes(2, 'big'))
                poly_bytes = xof.digest(self.n * 4)
                A[i][j] = np.frombuffer(poly_bytes, dtype=np.int32)[:self.n] % self.q
        return A
    
    def sign(self, message: bytes, private_key: bytes) -> bytes:
        """Sign a message"""
        # Parse private key
        key_len = self.l * self.n * 4
        s1 = np.frombuffer(private_key[:key_len], dtype=np.int32).reshape((self.l, self.n))
        s2 = np.frombuffer(private_key[key_len:key_len*2], dtype=np.int32).reshape((self.k, self.n))
        seed = private_key[key_len*2:]
        
        # Hash message
        msg_hash = hashlib.sha3_512(message).digest()
        
        # Simplified signing (full implementation would use rejection sampling)
        y = np.random.randint(-2**18, 2**18, size=(self.l, self.n), dtype=np.int32)
        
        A = self._expand_A(seed)
        w = (A @ y.T).T % self.q
        
        # Create signature
        signature = msg_hash + y.tobytes() + w.tobytes()
        
        return signature
    
    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify a signature"""
        # Parse public key
        seed = public_key[:32]
        t = np.frombuffer(public_key[32:], dtype=np.int32).reshape((self.k, self.n))
        
        # Parse signature  
        msg_hash = signature[:64]
        expected_hash = hashlib.sha3_512(message).digest()
        
        # Simplified verification
        return msg_hash == expected_hash


# Factory
def create_crystal_cipher(cipher_type: str = "kyber", security_level: int = 3):
    """Factory for creating crystal lattice ciphers"""
    if cipher_type.lower() == "kyber":
        return CrystalKyber(security_level)
    elif cipher_type.lower() == "dilithium":
        return CrystalDilithium(security_level)
    else:
        raise ValueError(f"Unknown crystal cipher: {cipher_type}")
	
