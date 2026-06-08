"""
CipherDSL - Domain Specific Language for Cipher Composition
Allows chaining, layering, and complex cipher orchestration
"""
import json
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class CipherMode(Enum):
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"


@dataclass
class CipherOp:
    """Represents a single cipher operation"""
    cipher_name: str
    cipher_type: str  # 'classical', 'advanced', 'homomorphic', 'crystal'
    key: Any
    mode: CipherMode
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CipherChain:
    """Chain of cipher operations"""
    operations: List[CipherOp] = field(default_factory=list)
    name: str = "unnamed_chain"
    description: str = ""
    
    def add(self, cipher_name: str, cipher_type: str, key: Any, 
            mode: CipherMode = CipherMode.ENCRYPT, **params) -> 'CipherChain':
        """Add a cipher operation to the chain"""
        self.operations.append(CipherOp(
            cipher_name=cipher_name,
            cipher_type=cipher_type,
            key=key,
            mode=mode,
            params=params
        ))
        return self
    
    def encrypt(self, cipher_name: str, cipher_type: str, key: Any, **params) -> 'CipherChain':
        """Add encryption operation"""
        return self.add(cipher_name, cipher_type, key, CipherMode.ENCRYPT, **params)
    
    def decrypt(self, cipher_name: str, cipher_type: str, key: Any, **params) -> 'CipherChain':
        """Add decryption operation"""
        return self.add(cipher_name, cipher_type, key, CipherMode.DECRYPT, **params)
    
    def reverse(self) -> 'CipherChain':
        """Create a reversed chain (for decryption)"""
        reversed_chain = CipherChain(name=f"{self.name}_reversed")
        for op in reversed(self.operations):
            # Flip the mode
            new_mode = CipherMode.DECRYPT if op.mode == CipherMode.ENCRYPT else CipherMode.ENCRYPT
            reversed_chain.operations.append(CipherOp(
                cipher_name=op.cipher_name,
                cipher_type=op.cipher_type,
                key=op.key,
                mode=new_mode,
                params=op.params
            ))
        return reversed_chain
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'operations': [
                {
                    'cipher_name': op.cipher_name,
                    'cipher_type': op.cipher_type,
                    'key': str(op.key),
                    'mode': op.mode.value,
                    'params': op.params
                }
                for op in self.operations
            ]
        }
    
    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CipherChain':
        """Deserialize from dictionary"""
        chain = cls(name=data.get('name', 'unnamed'), 
                   description=data.get('description', ''))
        
        for op_data in data.get('operations', []):
            chain.operations.append(CipherOp(
                cipher_name=op_data['cipher_name'],
                cipher_type=op_data['cipher_type'],
                key=op_data['key'],
                mode=CipherMode(op_data['mode']),
                params=op_data.get('params', {})
            ))
        
        return chain
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CipherChain':
        """Deserialize from JSON"""
        return cls.from_dict(json.loads(json_str))


class CipherDSL:
    """
    DSL for cipher composition and execution
    Supports natural language-like cipher chain building
    """
    
    def __init__(self):
        self.chains: Dict[str, CipherChain] = {}
        self.cipher_factories = {}
        self._register_default_factories()
    
    def _register_default_factories(self):
        """Register default cipher factory functions"""
        # These will be populated by the engine
        pass
    
    def register_cipher_factory(self, cipher_type: str, factory: Callable):
        """Register a cipher factory function"""
        self.cipher_factories[cipher_type] = factory
    
    def create_chain(self, name: str, description: str = "") -> CipherChain:
        """Create a new cipher chain"""
        chain = CipherChain(name=name, description=description)
        self.chains[name] = chain
        return chain
    
    def get_chain(self, name: str) -> CipherChain:
        """Retrieve a saved chain"""
        return self.chains.get(name)
    
    def save_chain(self, chain: CipherChain, filepath: str):
        """Save chain to file"""
        with open(filepath, 'w') as f:
            f.write(chain.to_json())
    
    def load_chain(self, filepath: str) -> CipherChain:
        """Load chain from file"""
        with open(filepath, 'r') as f:
            chain = CipherChain.from_json(f.read())
            self.chains[chain.name] = chain
            return chain
    
    def execute_operation(self, operation: CipherOp, data: Any) -> Any:
        """Execute a single cipher operation"""
        factory = self.cipher_factories.get(operation.cipher_type)
        if not factory:
            raise ValueError(f"No factory registered for cipher type: {operation.cipher_type}")
        
        cipher = factory(operation.cipher_name, **operation.params)
        
        if operation.mode == CipherMode.ENCRYPT:
            return cipher.encrypt(data, operation.key)
        else:
            return cipher.decrypt(data, operation.key)
    
    def execute_chain(self, chain: CipherChain, data: Any) -> Any:
        """Execute entire cipher chain"""
        result = data
        for operation in chain.operations:
            result = self.execute_operation(operation, result)
        return result
    
    def parse_dsl(self, dsl_string: str) -> CipherChain:
        """
        Parse DSL string into cipher chain
        
        Example DSL:
        CHAIN "secure_comm"
        ENCRYPT vigenere WITH "SECRETKEY"
        ENCRYPT aes WITH "0123456789ABCDEF"
        ENCRYPT caesar WITH "13"
        END
        """
        lines = [line.strip() for line in dsl_string.split('\n') if line.strip()]
        
        chain = None
        
        for line in lines:
            tokens = line.split()
            
            if not tokens:
                continue
            
            command = tokens[0].upper()
            
            if command == 'CHAIN':
                name = tokens[1].strip('"')
                chain = CipherChain(name=name)
            
            elif command == 'ENCRYPT' and chain:
                cipher_name = tokens[1]
                key_start = line.index('WITH') + 4
                key = line[key_start:].strip().strip('"')
                chain.encrypt(cipher_name, 'classical', key)
            
            elif command == 'DECRYPT' and chain:
                cipher_name = tokens[1]
                key_start = line.index('WITH') + 4
                key = line[key_start:].strip().strip('"')
                chain.decrypt(cipher_name, 'classical', key)
            
            elif command == 'END' and chain:
                self.chains[chain.name] = chain
                return chain
        
        return chain
    
    def visualize_chain(self, chain: CipherChain) -> str:
        """Create ASCII visualization of cipher chain"""
        viz = []
        viz.append(f"╔═══════════════════════════════════════╗")
        viz.append(f"║  Chain: {chain.name:<28} ║")
        viz.append(f"╠═══════════════════════════════════════╣")
        
        for i, op in enumerate(chain.operations, 1):
            mode_symbol = "🔒" if op.mode == CipherMode.ENCRYPT else "🔓"
            viz.append(f"║ {i}. {mode_symbol} {op.cipher_name:<30} ║")
            viz.append(f"║    Type: {op.cipher_type:<27} ║")
            viz.append(f"║    Key: {str(op.key)[:30]:<30} ║")
            if i < len(chain.operations):
                viz.append(f"║           ↓                         ║")
        
        viz.append(f"╚═══════════════════════════════════════╝")
        
        return '\n'.join(viz)


class CipherPolicy:
    """Security policy for cipher selection and enforcement"""
    
    def __init__(self):
        self.min_key_length = 8
        self.required_cipher_types = []
        self.forbidden_ciphers = []
        self.require_homomorphic = False
        self.require_quantum_resistant = False
    
    def validate_chain(self, chain: CipherChain) -> tuple[bool, List[str]]:
        """Validate cipher chain against policy"""
        violations = []
        
        # Check for quantum resistance requirement
        if self.require_quantum_resistant:
            has_crystal = any(op.cipher_type == 'crystal' for op in chain.operations)
            if not has_crystal:
                violations.append("Policy requires quantum-resistant cipher")
        
        # Check for homomorphic requirement
        if self.require_homomorphic:
            has_homomorphic = any(op.cipher_type == 'homomorphic' for op in chain.operations)
            if not has_homomorphic:
                violations.append("Policy requires homomorphic cipher")
        
        # Check forbidden ciphers
        for op in chain.operations:
            if op.cipher_name in self.forbidden_ciphers:
                violations.append(f"Cipher '{op.cipher_name}' is forbidden by policy")
        
        # Check required types
        for req_type in self.required_cipher_types:
            if not any(op.cipher_type == req_type for op in chain.operations):
                violations.append(f"Policy requires cipher type: {req_type}")
        
        return len(violations) == 0, violations
    
    def enforce(self, chain: CipherChain) -> CipherChain:
        """Enforce policy by adding required ciphers"""
        is_valid, violations = self.validate_chain(chain)
        
        if is_valid:
            return chain
        
        # Auto-fix by adding required ciphers
        if self.require_quantum_resistant:
            has_crystal = any(op.cipher_type == 'crystal' for op in chain.operations)
            if not has_crystal:
                # Add Kyber at the end
                chain.operations.append(CipherOp(
                    cipher_name='kyber',
                    cipher_type='crystal',
                    key='auto_generated',
                    mode=CipherMode.ENCRYPT
                ))
        
        if self.require_homomorphic:
            has_homomorphic = any(op.cipher_type == 'homomorphic' for op in chain.operations)
            if not has_homomorphic:
                # Add Paillier at the beginning
                chain.operations.insert(0, CipherOp(
                    cipher_name='paillier',
                    cipher_type='homomorphic',
                    key='auto_generated',
                    mode=CipherMode.ENCRYPT
                ))
        
        return chain


class CipherTemplate:
    """Predefined cipher chain templates"""
    
    @staticmethod
    def high_security() -> CipherChain:
        """High security template with quantum resistance"""
        chain = CipherChain(name="high_security", 
                          description="Quantum-resistant multi-layer encryption")
        chain.encrypt('kyber', 'crystal', 'auto')
        chain.encrypt('aes256', 'modern', 'auto')
        chain.encrypt('vigenere', 'classical', 'COMPLEXKEY')
        return chain
    
    @staticmethod
    def stealth() -> CipherChain:
        """Stealth communication template"""
        chain = CipherChain(name="stealth",
                          description="Multiple classical ciphers for obfuscation")
        chain.encrypt('vigenere', 'classical', 'KEY1')
        chain.encrypt('playfair', 'classical', 'KEY2')
        chain.encrypt('adfgvx', 'advanced', 'KEY3,KEY4')
        chain.encrypt('columnar', 'classical', 'KEY5')
        return chain
    
    @staticmethod
    def privacy_preserving() -> CipherChain:
        """Homomorphic encryption for privacy-preserving computation"""
        chain = CipherChain(name="privacy_preserving",
                          description="Allows computation on encrypted data")
        chain.encrypt('paillier', 'homomorphic', 'auto')
        return chain
    
    @staticmethod
    def military_grade() -> CipherChain:
        """Military-grade multi-layer encryption"""
        chain = CipherChain(name="military_grade",
                          description="DoD-grade encryption stack")
        chain.encrypt('kyber', 'crystal', 'auto')  # Quantum resistant
        chain.encrypt('adfgvx', 'advanced', 'KEY1,KEY2')  # Historical military
        chain.encrypt('aes256', 'modern', 'auto')
        chain.encrypt('twofish', 'modern', 'auto')
        return chain


# DSL Parser with more features
class AdvancedDSLParser:
    """Advanced DSL parser with conditionals and loops"""
    
    @staticmethod
    def parse(dsl: str) -> CipherChain:
        """Parse advanced DSL with variables and conditionals"""
        # This would implement a full parser
        # For now, basic implementation
        pass
    
    @staticmethod
    def compile(chain: CipherChain) -> str:
        """Compile chain to executable code"""
        code_lines = []
        code_lines.append("# Auto-generated cipher chain")
        code_lines.append(f"# Chain: {chain.name}")
        code_lines.append("")
        
        for i, op in enumerate(chain.operations):
            var_name = f"result_{i}"
            prev_var = f"result_{i-1}" if i > 0 else "plaintext"
            
            code_lines.append(f"# Operation {i+1}: {op.mode.value} {op.cipher_name}")
            code_lines.append(f"cipher_{i} = get_cipher('{op.cipher_name}', '{op.cipher_type}')")
            code_lines.append(f"{var_name} = cipher_{i}.{op.mode.value}({prev_var}, '{op.key}')")
            code_lines.append("")
        
        code_lines.append(f"ciphertext = result_{len(chain.operations)-1}")
        
        return '\n'.join(code_lines)
