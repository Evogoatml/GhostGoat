# QUICK START GUIDE
## Quantum-Adaptive Crypto Orchestrator

### 🚀 5-Minute Setup

#### Step 1: Install Dependencies
```bash
pip install pycryptodome numpy --break-system-packages
```

#### Step 2: Clone Repositories (Optional - for full AI training)
```bash
cd quantum-adaptive-crypto-orchestrator
./setup.sh
```

Or manually clone just what you need:
```bash
cd ai_resources/ml_algorithms
git clone https://github.com/milaan9/Machine_Learning_Algorithms_from_Scratch.git .
```

#### Step 3: Run Tests
```bash
python3 test_audit.py
```

#### Step 4: Run Demo
```bash
python3 main.py
```

### ⚡ Basic Usage

#### Encrypt Data
```python
from main import QuantumAdaptiveSystem

system = QuantumAdaptiveSystem()

# Adaptive encryption
encrypted = system.adaptive_encrypt(
    plaintext=b"Your secret data",
    sensitivity=8,
    performance_priority=5
)

# Decrypt
decrypted = system.adaptive_decrypt(encrypted)
```

#### Use Individual Components

**Crypto Only:**
```python
from crypto_engine.mutating_cipher import MutatingCryptoEngine

engine = MutatingCryptoEngine()
encrypted = engine.encrypt_mutating(b"data")
decrypted = engine.decrypt_mutating(encrypted)
```

**AI Orchestrator Only:**
```python
from ai_orchestrator.agentic_rag import AIOrchestrator, DecisionContext

orchestrator = AIOrchestrator()
context = DecisionContext(threat_level=8, data_sensitivity=9, 
                         performance_priority=5, network_state={}, 
                         historical_attacks=[])
decision = orchestrator.decide_crypto_pipeline(context)
```

**Network Defense Only:**
```python
from network_security.adaptive_defense import AdaptiveNetworkDefense, PortConfig

defense = AdaptiveNetworkDefense()
defense.configure_port(PortConfig(port=8080, is_honeypot=True, 
                                  real_backend=None, sandbox_enabled=False,
                                  service_banner="HTTP"))
```

### 🎯 Quick Integration

#### With GhostGoatNode
```python
# In your GhostGoatNode brain module:
from quantum_adaptive.crypto_engine.mutating_cipher import MutatingCryptoEngine

class EnhancedBrainModule:
    def __init__(self):
        self.crypto = MutatingCryptoEngine()
    
    def save_state(self, brain_state):
        encrypted = self.crypto.encrypt_mutating(brain_state)
        # Store encrypted data
```

#### With META GOAT V2
```python
# Add as agent in your orchestrator:
from quantum_adaptive.ai_orchestrator.agentic_rag import AIOrchestrator

class CryptoAgent:
    def __init__(self):
        self.orchestrator = AIOrchestrator()
    
    def decide_security_level(self, task_context):
        return self.orchestrator.decide_crypto_pipeline(task_context)
```

### 📊 Quick Tests

Run specific test categories:

```bash
# All tests
python3 test_audit.py

# Just crypto tests (edit test_audit.py to comment out others)
python3 -c "from test_audit import *; suite = ComprehensiveTestSuite(); suite.test_crypto_engine()"
```

### 🔧 Configuration Quick Reference

```python
config = {
    "vector_db_path": "/tmp/qac_memory.pkl",  # Memory storage
    "auto_learn": True,                        # Learn from operations
    "mutation_frequency": "dynamic",           # Cipher mutation
    "default_threat_level": 5,                 # Baseline (0-10)
    "enable_network_defense": False            # Network features
}
```

### 🎨 Threat Level Guide

| Level | Description | Use Case |
|-------|-------------|----------|
| 0-2   | Minimal     | Public data, low-risk environments |
| 3-5   | Moderate    | Internal systems, standard operations |
| 6-7   | Elevated    | Sensitive data, known threats |
| 8-9   | High        | Critical systems, active threats |
| 10    | Maximum     | Top secret, nation-state threats |

### 📈 Performance Tuning

**For Speed:**
```python
encrypted = system.adaptive_encrypt(
    data,
    sensitivity=3,
    performance_priority=10  # Maximum performance
)
```

**For Security:**
```python
encrypted = system.adaptive_encrypt(
    data,
    sensitivity=10,
    performance_priority=1,  # Maximum security
    threat_context={'threat_level': 10}
)
```

### 🛡️ Network Defense Quick Setup

```python
system.configure_network_defense(
    honeypot_ports=[(2222, "SSH"), (8080, "HTTP")],
    sandbox_ports=[(3306, "MySQL")]
)

# Requires root for ports < 1024
# Use sudo or ports > 1024
```

### 📝 Common Tasks

**Export System Status:**
```python
status = system.get_system_status()
system.export_audit_report("/tmp/audit.json")
```

**Train from Custom Data:**
```python
system.ai_orchestrator.vector_db.add(
    "Custom security knowledge",
    {"category": "custom", "confidence": 0.9}
)
```

**Learn from Attacks:**
```python
system.ai_orchestrator.learn_from_attack(
    "ddos", "blocked", {"source": "192.168.1.1"}
)
```

### 🐛 Troubleshooting

**ModuleNotFoundError:**
```bash
export PYTHONPATH=/path/to/quantum-adaptive-crypto-orchestrator:$PYTHONPATH
```

**Crypto Import Error:**
```bash
pip uninstall pycrypto pycryptodome
pip install pycryptodome --break-system-packages
```

**Permission Denied (Network):**
- Use ports > 1024, or
- Run with `sudo python3 main.py`

### 📚 Next Steps

1. Read full documentation: `DOCUMENTATION.md`
2. Explore test suite: `test_audit.py`
3. Check examples in: `main.py`
4. Integrate with your projects

### 💡 Pro Tips

- Start with default config, tune based on metrics
- Monitor decision history for optimization
- Use auto_learn=True for adaptive behavior
- Export audit reports regularly
- Test with your actual data patterns

---

**Need Help?** Check `DOCUMENTATION.md` for detailed guides
**Want More?** See individual module files for advanced API usage
