#!/usr/bin/env python3
"""
AI Orchestrator with RAG and Cognitive Vector Memory
Agentic decision-making for crypto pipeline selection and network defense
"""

import json
import hashlib
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import pickle
import os


@dataclass
class MemoryVector:
    """Cognitive memory vector for pattern storage"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    timestamp: float
    access_count: int = 0
    
    def similarity(self, other_embedding: List[float]) -> float:
        """Cosine similarity between embeddings"""
        a = np.array(self.embedding)
        b = np.array(other_embedding)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


@dataclass
class DecisionContext:
    """Context for orchestrator decisions"""
    threat_level: int  # 0-10
    data_sensitivity: int  # 0-10
    performance_priority: int  # 0-10
    network_state: Dict[str, Any]
    historical_attacks: List[str]


class SimpleVectorDB:
    """Lightweight vector database for cognitive memory"""
    
    def __init__(self, storage_path: str = "/tmp/vector_memory.pkl"):
        self.storage_path = storage_path
        self.vectors: List[MemoryVector] = []
        self.load()
    
    def _simple_embedding(self, text: str, dim: int = 128) -> List[float]:
        """
        Simple deterministic embedding using hash-based approach
        For production, replace with actual embeddings (sentence-transformers, etc.)
        """
        # Create multiple hash values for different dimensions
        embeddings = []
        for i in range(dim):
            hash_input = f"{text}_{i}".encode()
            hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)
            # Normalize to [-1, 1]
            normalized = (hash_val % 1000) / 500.0 - 1.0
            embeddings.append(normalized)
        
        # Normalize vector
        norm = np.linalg.norm(embeddings)
        return [e / norm for e in embeddings] if norm > 0 else embeddings
    
    def add(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Add content to vector memory"""
        vector_id = hashlib.sha256(f"{content}{datetime.now()}".encode()).hexdigest()[:16]
        embedding = self._simple_embedding(content)
        
        vector = MemoryVector(
            id=vector_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            timestamp=datetime.now().timestamp()
        )
        
        self.vectors.append(vector)
        self.save()
        return vector_id
    
    def search(self, query: str, top_k: int = 5) -> List[MemoryVector]:
        """Semantic search for similar vectors"""
        query_embedding = self._simple_embedding(query)
        
        # Calculate similarities
        scored_vectors = []
        for vector in self.vectors:
            score = vector.similarity(query_embedding)
            scored_vectors.append((score, vector))
            vector.access_count += 1
        
        # Sort by similarity
        scored_vectors.sort(reverse=True, key=lambda x: x[0])
        
        self.save()
        return [v for _, v in scored_vectors[:top_k]]
    
    def save(self):
        """Persist vector database"""
        try:
            with open(self.storage_path, 'wb') as f:
                pickle.dump(self.vectors, f)
        except Exception as e:
            print(f"Warning: Could not save vector DB: {e}")
    
    def load(self):
        """Load vector database from disk"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'rb') as f:
                    self.vectors = pickle.load(f)
        except Exception as e:
            print(f"Warning: Could not load vector DB: {e}")
            self.vectors = []


class RAGSystem:
    """Retrieval-Augmented Generation for crypto decisions"""
    
    def __init__(self, vector_db: SimpleVectorDB):
        self.vector_db = vector_db
        self.initialize_knowledge_base()
    
    def initialize_knowledge_base(self):
        """Seed vector DB with crypto and security knowledge"""
        knowledge = [
            {
                "content": "AES-256-GCM provides authenticated encryption with high performance, ideal for bulk data encryption",
                "metadata": {"category": "cipher", "performance": 9, "security": 9}
            },
            {
                "content": "ChaCha20-Poly1305 is resistant to timing attacks and performs well on systems without AES hardware acceleration",
                "metadata": {"category": "cipher", "performance": 8, "security": 9}
            },
            {
                "content": "Multi-layer encryption with different algorithms increases security against cryptanalysis",
                "metadata": {"category": "strategy", "security": 10}
            },
            {
                "content": "Manchester encoding adds obfuscation layer and helps detect bit corruption",
                "metadata": {"category": "encoding", "integrity": 8}
            },
            {
                "content": "Rolling codes prevent replay attacks and ensure forward secrecy",
                "metadata": {"category": "key_management", "security": 9}
            },
            {
                "content": "High threat levels require multiple cipher layers and frequent key rotation",
                "metadata": {"category": "threat_response", "threat_level": 8}
            },
            {
                "content": "Performance-critical operations should use single-layer AES-GCM with hardware acceleration",
                "metadata": {"category": "optimization", "performance": 10}
            },
            {
                "content": "Port hopping and honeypots effectively divert automated attack tools",
                "metadata": {"category": "network_defense", "security": 8}
            },
            {
                "content": "Sandboxing suspicious connections prevents lateral movement in network breaches",
                "metadata": {"category": "network_defense", "security": 9}
            },
            {
                "content": "SHA-3 and BLAKE2 provide post-quantum resistant hashing",
                "metadata": {"category": "hashing", "quantum_safe": True, "security": 9}
            }
        ]
        
        for item in knowledge:
            self.vector_db.add(item["content"], item["metadata"])
    
    def retrieve_relevant_knowledge(self, query: str, top_k: int = 3) -> List[MemoryVector]:
        """Retrieve relevant knowledge for decision-making"""
        return self.vector_db.search(query, top_k)
    
    def augmented_decision(self, context: DecisionContext, query: str) -> Dict[str, Any]:
        """Make augmented decision using retrieved knowledge"""
        # Retrieve relevant knowledge
        relevant_memories = self.retrieve_relevant_knowledge(query, top_k=5)
        
        # Build decision based on context and knowledge
        decision = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "context": asdict(context),
            "retrieved_knowledge": [
                {
                    "content": m.content,
                    "relevance_score": m.similarity(self.vector_db._simple_embedding(query)),
                    "metadata": m.metadata
                }
                for m in relevant_memories
            ],
            "recommendation": self._generate_recommendation(context, relevant_memories)
        }
        
        return decision
    
    def _generate_recommendation(self, context: DecisionContext, memories: List[MemoryVector]) -> Dict[str, Any]:
        """Generate recommendation based on context and retrieved knowledge"""
        # Scoring system for cipher selection
        cipher_scores = {
            "aes_256_gcm": 0,
            "chacha20_poly1305": 0,
            "multi_layer": 0
        }
        
        manchester_score = 0
        
        # Analyze context
        if context.threat_level > 7:
            cipher_scores["multi_layer"] += 30
            manchester_score += 20
        
        if context.data_sensitivity > 8:
            cipher_scores["multi_layer"] += 20
            manchester_score += 15
        
        if context.performance_priority > 7:
            cipher_scores["aes_256_gcm"] += 25
            cipher_scores["multi_layer"] -= 15
        
        # Incorporate retrieved knowledge
        for memory in memories:
            meta = memory.metadata
            if meta.get("category") == "cipher":
                if "AES" in memory.content:
                    cipher_scores["aes_256_gcm"] += 10
                if "ChaCha20" in memory.content:
                    cipher_scores["chacha20_poly1305"] += 10
            
            if meta.get("category") == "strategy" and "Multi-layer" in memory.content:
                cipher_scores["multi_layer"] += 15
            
            if "Manchester" in memory.content:
                manchester_score += 10
        
        # Make recommendation
        recommended_cipher = max(cipher_scores, key=cipher_scores.get)
        
        return {
            "cipher_strategy": recommended_cipher,
            "use_manchester": manchester_score > 20,
            "manchester_layers": min(3, manchester_score // 15) if manchester_score > 20 else 0,
            "key_rotation_interval": "high" if context.threat_level > 7 else "medium",
            "confidence": min(100, max(cipher_scores.values())),
            "reasoning": self._explain_reasoning(context, cipher_scores, manchester_score)
        }
    
    def _explain_reasoning(self, context: DecisionContext, scores: Dict, manchester_score: int) -> str:
        """Generate human-readable reasoning"""
        reasons = []
        
        if context.threat_level > 7:
            reasons.append(f"High threat level ({context.threat_level}/10) requires enhanced security")
        
        if context.data_sensitivity > 8:
            reasons.append(f"High data sensitivity ({context.data_sensitivity}/10) demands multi-layer protection")
        
        if context.performance_priority > 7:
            reasons.append(f"Performance priority ({context.performance_priority}/10) favors optimized ciphers")
        
        if manchester_score > 20:
            reasons.append("Manchester encoding recommended for additional obfuscation")
        
        return "; ".join(reasons) if reasons else "Standard security posture recommended"


class AIOrchestrator:
    """Main agentic orchestrator for crypto and network decisions"""
    
    def __init__(self, vector_db_path: str = None):
        db_path = vector_db_path or "/tmp/orchestrator_memory.pkl"
        self.vector_db = SimpleVectorDB(db_path)
        self.rag_system = RAGSystem(self.vector_db)
        self.decision_history: List[Dict] = []
        
    def learn_from_attack(self, attack_type: str, effectiveness: str, context: Dict):
        """Learn from observed attacks"""
        learning = f"Attack type '{attack_type}' was {effectiveness}. Context: {json.dumps(context)}"
        self.vector_db.add(learning, {
            "category": "attack_pattern",
            "attack_type": attack_type,
            "effectiveness": effectiveness,
            "timestamp": datetime.now().timestamp()
        })
    
    def learn_from_success(self, strategy: str, outcome: str):
        """Learn from successful defenses"""
        learning = f"Defense strategy '{strategy}' resulted in {outcome}"
        self.vector_db.add(learning, {
            "category": "defense_pattern",
            "strategy": strategy,
            "outcome": outcome,
            "timestamp": datetime.now().timestamp()
        })
    
    def decide_crypto_pipeline(self, context: DecisionContext) -> Dict[str, Any]:
        """
        Make agentic decision about crypto pipeline configuration
        
        Returns:
            Dictionary with recommended cipher configuration
        """
        query = f"""
        Threat level {context.threat_level}, 
        sensitivity {context.data_sensitivity}, 
        performance {context.performance_priority}.
        What crypto strategy?
        """
        
        decision = self.rag_system.augmented_decision(context, query)
        self.decision_history.append(decision)
        
        return decision
    
    def decide_network_defense(self, context: DecisionContext) -> Dict[str, Any]:
        """Decide network defense strategy"""
        query = f"Network defense for threat level {context.threat_level}"
        
        decision = self.rag_system.augmented_decision(context, query)
        
        # Add network-specific recommendations
        recommendation = decision["recommendation"]
        recommendation["honeypot_enabled"] = context.threat_level > 5
        recommendation["port_hopping"] = context.threat_level > 7
        recommendation["sandbox_all"] = context.threat_level > 8
        
        return decision
    
    def get_decision_history(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent decision history"""
        return self.decision_history[-limit:]
    
    def export_memory(self, filepath: str):
        """Export cognitive memory to file"""
        data = {
            "vectors": [asdict(v) for v in self.vector_db.vectors],
            "decision_history": self.decision_history
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


def demo():
    """Demo the AI orchestrator"""
    print("=== AI Orchestrator with RAG Demo ===\n")
    
    # Initialize orchestrator
    orchestrator = AIOrchestrator()
    
    # Test case 1: High security scenario
    print("Scenario 1: High Threat, High Sensitivity")
    context1 = DecisionContext(
        threat_level=9,
        data_sensitivity=10,
        performance_priority=3,
        network_state={"active_connections": 50, "suspicious_ips": 5},
        historical_attacks=["port_scan", "brute_force"]
    )
    
    crypto_decision = orchestrator.decide_crypto_pipeline(context1)
    print(f"Recommended: {crypto_decision['recommendation']['cipher_strategy']}")
    print(f"Manchester: {crypto_decision['recommendation']['use_manchester']} "
          f"({crypto_decision['recommendation']['manchester_layers']} layers)")
    print(f"Reasoning: {crypto_decision['recommendation']['reasoning']}\n")
    
    # Test case 2: Performance-critical scenario
    print("Scenario 2: Low Threat, High Performance Priority")
    context2 = DecisionContext(
        threat_level=2,
        data_sensitivity=4,
        performance_priority=10,
        network_state={"active_connections": 1000, "suspicious_ips": 0},
        historical_attacks=[]
    )
    
    crypto_decision = orchestrator.decide_crypto_pipeline(context2)
    print(f"Recommended: {crypto_decision['recommendation']['cipher_strategy']}")
    print(f"Manchester: {crypto_decision['recommendation']['use_manchester']}")
    print(f"Reasoning: {crypto_decision['recommendation']['reasoning']}\n")
    
    # Learn from experience
    print("Learning from attack...")
    orchestrator.learn_from_attack(
        "sql_injection",
        "blocked",
        {"source_ip": "192.168.1.100", "target": "api_endpoint"}
    )
    
    orchestrator.learn_from_success(
        "multi_layer_encryption",
        "successfully prevented data exfiltration"
    )
    
    # Network defense decision
    print("\nNetwork Defense Decision:")
    network_decision = orchestrator.decide_network_defense(context1)
    net_rec = network_decision['recommendation']
    print(f"Honeypot: {net_rec['honeypot_enabled']}")
    print(f"Port hopping: {net_rec['port_hopping']}")
    print(f"Sandbox all: {net_rec['sandbox_all']}")
    
    print(f"\nTotal vectors in memory: {len(orchestrator.vector_db.vectors)}")
    print(f"Decisions made: {len(orchestrator.decision_history)}")


if __name__ == "__main__":
    demo()
