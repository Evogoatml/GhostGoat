# CRYSTALS Family Post-Quantum Cryptography System

A complete post-quantum cryptographic system implementing the NIST-selected CRYSTALS suite:
- **CRYSTALS-Kyber**: Key Encapsulation Mechanism (KEM) for secure key exchange
- **CRYSTALS-Dilithium**: Digital Signature Algorithm for authentication

## 🔐 What is CRYSTALS?

**CRYSTALS** = **C**ryptographic **S**uite for **A**lgebraic **L**attices

The CRYSTALS suite provides post-quantum security, meaning it's resistant to attacks from both classical and quantum computers. These algorithms are based on lattice cryptography, specifically the Module Learning With Errors (MLWE) and Module Short Integer Solution (MSIS) problems.

### Why CRYSTALS?

1. **Post-Quantum Security**: Resistant to Shor's algorithm and quantum attacks
2. **NIST Standardized**: Selected by NIST for PQC standardization (2022)
3. **Efficient**: Fast operations, small key sizes
4. **Proven Security**: Strong security proofs based on lattice problems

## 🚀 Quick Start

### One-Command Installation

```bash
./install.sh
```

This will:
- Install all dependencies
- Set up Python virtual environment  
- Build and install liboqs (Open Quantum Safe)
- Configure the CRYSTALS crypto system

### Activate Environment

```bash
source ~/crystal_env/bin/activate
```

### Run Tests

```bash
python3 crystal_system.py --test
```

## 📖 Usage Examples

### Generate Keypairs

```bash
python3 crystal_system.py --keygen
```

This creates:
- `my_kem_public.key` / `my_kem_private.key` (Kyber keys)
- `my_sig_public.key` / `my_sig_private.key` (Dilithium keys)

### Encrypt a File

```bash
python3 crystal_system.py --encrypt sensitive.pdf --public-key recipient_kem --output encrypted.json
```

### Decrypt a File

```bash
python3 crystal_system.py --decrypt encrypted.json --private-key my_kem --output decrypted.pdf
```

### Python API Usage

```python
from crystal_system import HybridCryptoSystem

# Initialize system
crypto = HybridCryptoSystem()

# Generate keypairs for Alice and Bob
alice_keys = crypto.generate_keypairs()
bob_keys = crypto.generate_keypairs()

# Alice encrypts message for Bob (with signature)
message = b"Secret message"
encrypted = crypto.encrypt(
    message,
    bob_keys['kem'].public_key,
    alice_keys['sig'].private_key  # Optional: sign the message
)

# Bob decrypts and verifies
decrypted = crypto.decrypt(
    encrypted,
    bob_keys['kem'].private_key,
    alice_keys['sig'].public_key  # Optional: verify signature
)

print(decrypted)  # b"Secret message"
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         CRYSTALS-Kyber (KEM)            │
│  ┌─────────────────────────────────┐   │
│  │  1. Encapsulate(public_key)     │   │
│  │     → (ciphertext, shared_secret)│   │
│  │                                   │   │
│  │  2. Decapsulate(ciphertext,      │   │
│  │                 private_key)      │   │
│  │     → shared_secret              │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    ↓
         Derive AES-256 Key from Shared Secret
                    ↓
┌─────────────────────────────────────────┐
│         AES-256-GCM Encryption          │
│   Fast symmetric encryption of data     │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      CRYSTALS-Dilithium (Optional)      │
│  ┌─────────────────────────────────┐   │
│  │  Sign(message, private_key)     │   │
│  │     → signature                  │   │
│  │                                   │   │
│  │  Verify(message, signature,      │   │
│  │         public_key)               │   │
│  │     → true/false                 │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 🔬 Technical Details

### CRYSTALS-Kyber

**Security Levels:**
- Kyber-512: NIST Level 1 (equivalent to AES-128)
- Kyber-768: NIST Level 3 (equivalent to AES-192) ← **Default**
- Kyber-1024: NIST Level 5 (equivalent to AES-256)

**Key Sizes (Kyber-768):**
- Public key: 1,184 bytes
- Private key: 2,400 bytes
- Ciphertext: 1,088 bytes
- Shared secret: 32 bytes

**Performance:**
- Keygen: ~50,000 ops/sec
- Encapsulate: ~70,000 ops/sec
- Decapsulate: ~50,000 ops/sec

### CRYSTALS-Dilithium

**Security Levels:**
- Dilithium2: NIST Level 2
- Dilithium3: NIST Level 3 ← **Default**
- Dilithium5: NIST Level 5

**Key Sizes (Dilithium3):**
- Public key: 1,952 bytes
- Private key: 4,000 bytes
- Signature: 3,293 bytes

**Performance:**
- Sign: ~2,500 ops/sec
- Verify: ~5,000 ops/sec

## 🔧 Advanced Configuration

### Change Security Level

```python
# Use Kyber-1024 for maximum security
crypto = HybridCryptoSystem(kyber_variant='kyber1024')

# Use Dilithium5 for signatures
dilithium = CrystalsDilithium(variant='dilithium5')
```

### Batch Operations

```python
# Encrypt multiple files
files = ['doc1.pdf', 'doc2.txt', 'doc3.jpg']
for file in files:
    with open(file, 'rb') as f:
        data = f.read()
    encrypted = crypto.encrypt(data, recipient_public_key)
    with open(f'{file}.enc', 'w') as f:
        json.dump(encrypted, f)
```

## 🛡️ Security Features

### Post-Quantum Resistance
- Resistant to Shor's algorithm
- Resistant to Grover's algorithm
- Based on lattice problems (MLWE/MSIS)

### Authenticated Encryption
- AES-256-GCM for data encryption
- Built-in authentication tag
- Prevents tampering and replay attacks

### Forward Secrecy
- Each encryption uses a fresh ephemeral key
- Compromise of long-term keys doesn't affect past sessions

### Integrity Protection
- Dilithium signatures verify message authenticity
- Detects any tampering with ciphertext

## 📊 Comparison with Traditional Crypto

| Feature | RSA-2048 | ECDH P-256 | Kyber-768 |
|---------|----------|------------|-----------|
| Quantum Safe | ❌ No | ❌ No | ✅ Yes |
| Public Key | 256 bytes | 64 bytes | 1,184 bytes |
| Keygen Speed | Slow | Fast | Very Fast |
| Standardized | ✅ Yes | ✅ Yes | ✅ Yes (2024) |

## 🔐 Integration with Security Stack

This system integrates with the full security stack:

```bash
# Run with monitoring
docker-compose up -d

# View encrypted traffic
curl http://localhost:5601  # Kibana dashboard

# Check security logs
docker-compose logs security_dashboard
```

## 📝 File Formats

### Encrypted Package (JSON)

```json
{
  "version": "1.0",
  "algorithm": "Kyber-AES-GCM",
  "kem_ciphertext": "base64_encoded...",
  "nonce": "base64_encoded...",
  "ciphertext": "base64_encoded...",
  "tag": "base64_encoded...",
  "timestamp": "2024-12-01T10:30:00",
  "signature": "base64_encoded..."  // Optional
}
```

### Key File Format

Keys are stored as binary files with metadata:
- `*_public.key`: Public key (binary)
- `*_private.key`: Private key (binary) 
- `*_meta.json`: Metadata (algorithm, creation date)

## 🧪 Testing

### Unit Tests

```bash
python3 crystal_system.py --test
```

### Performance Benchmarks

```bash
python3 -m pytest tests/benchmark_test.py
```

### Security Audit

```bash
# Run full security audit
python3 code_auditor/audit.py
```

## 🌐 Use Cases

### Secure Communications
- End-to-end encrypted messaging
- Secure email (PQC-enabled S/MIME)
- VPN with post-quantum key exchange

### Data Protection
- Encrypt sensitive files at rest
- Secure cloud storage
- Database encryption

### IoT Security
- Secure device provisioning
- Firmware signing and verification
- Secure sensor data transmission

### Blockchain & DLT
- Post-quantum secure transactions
- Quantum-resistant smart contracts
- Future-proof digital signatures

## 📚 Resources

### Official Standards
- [NIST PQC Project](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [CRYSTALS-Kyber Specification](https://pq-crystals.org/kyber/)
- [CRYSTALS-Dilithium Specification](https://pq-crystals.org/dilithium/)

### Research Papers
- "CRYSTALS-Kyber: A CCA-Secure Module-Lattice-Based KEM"
- "CRYSTALS-Dilithium: A Lattice-Based Digital Signature Scheme"

### Libraries Used
- [liboqs](https://github.com/open-quantum-safe/liboqs) - Open Quantum Safe
- [PyCryptodome](https://pycryptodome.readthedocs.io/) - AES encryption

## ⚠️ Security Considerations

### Key Management
- Store private keys securely (HSM, TPM, or encrypted storage)
- Never transmit private keys over networks
- Rotate keys periodically
- Use strong random number generators

### Quantum Timeline
- NIST recommends transitioning to PQC by 2030
- Large quantum computers may exist by 2030-2040
- "Harvest now, decrypt later" attacks are a current threat

### Hybrid Approach
For maximum security during transition:

```python
# Use both classical and post-quantum
def hybrid_encrypt(data, rsa_key, kyber_key):
    # Classical encryption
    rsa_encrypted = rsa_encrypt(data, rsa_key)
    
    # Post-quantum encryption
    kyber_encrypted = kyber_encrypt(rsa_encrypted, kyber_key)
    
    return kyber_encrypted
```

## 🤝 Contributing

Contributions welcome! Areas of interest:
- Performance optimizations
- Additional PQC algorithms (SPHINCS+, etc.)
- Hardware acceleration support
- Additional language bindings

## 📄 License

MIT License - see LICENSE file

## 🔔 Updates

- **v1.0.0** (2024): Initial release with Kyber-768 and Dilithium3
- NIST standardization: Expected 2024
- Hardware support: Coming in future releases

## 💬 Support

For questions or issues:
- GitHub Issues
- Security vulnerabilities: security@example.com

---

**Remember**: Cryptography is hard. Use this system as part of a comprehensive security strategy, not as the only layer of defense.
