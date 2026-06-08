"""GhostGoat DualBrain — Neural + Symbolic Cognitive Core."""
import json, time, uuid, hashlib, logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class CognitiveState:
    vector: List[float]
    symbolic_tags: List[str]
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MemoryNode:
    id: str
    content: str
    embedding: List[float]
    node_type: str = "fact"
    edges: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=time.time)

class NeuralCortex:
    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self.weights = [0.0] * dimension
        self.experience_buffer: List[CognitiveState] = []
        self.learning_rate = 0.01

    def encode(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = []
        for i in range(self.dimension):
            idx = (i * 2) % len(h)
            val = int(h[idx:idx+2], 16) / 255.0
            vec.append(val)
        return vec

    def decide(self, state_vector: List[float]) -> Tuple[str, float]:
        if not state_vector:
            return "explore", 0.5
        conf = sum(a * b for a, b in zip(state_vector, self.weights)) / max(1e-6, sum(abs(w) for w in self.weights))
        conf = max(0.0, min(1.0, conf))
        if conf > 0.7: return "exploit", conf
        elif conf > 0.4: return "reason", conf
        return "explore", conf

    def learn(self, state: CognitiveState, reward: float):
        self.experience_buffer.append(state)
        if len(self.experience_buffer) > 1000:
            self.experience_buffer = self.experience_buffer[-500:]
        for i, v in enumerate(state.vector):
            if i < len(self.weights):
                self.weights[i] += self.learning_rate * reward * v

    def get_state(self) -> Dict[str, Any]:
        return {"dimension": self.dimension, "experiences": len(self.experience_buffer),
                "weight_mean": sum(self.weights) / max(1, len(self.weights))}

class SymbolicCortex:
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self.facts: Dict[str, Any] = {}
        self.inference_log: List[str] = []

    def add_fact(self, key: str, value: Any, certainty: float = 1.0):
        self.facts[key] = {"value": value, "certainty": certainty, "time": time.time()}

    def add_rule(self, condition: str, action: str, priority: int = 5):
        self.rules.append({"condition": condition, "action": action, "priority": priority})
        self.rules.sort(key=lambda r: r["priority"])

    def infer(self, query: str) -> Optional[str]:
        for rule in self.rules:
            if rule["condition"] in query or query in rule["condition"]:
                self.inference_log.append(f"RULE_FIRED: {rule['action']}")
                return rule["action"]
        for k, v in self.facts.items():
            if k in query or query in k:
                return str(v["value"])
        return None

    def get_state(self) -> Dict[str, Any]:
        return {"facts": len(self.facts), "rules": len(self.rules), "inferences": len(self.inference_log)}

class DualBrain:
    def __init__(self, name: str = "ghostgoat", dimension: int = 128, config: Optional[Dict] = None):
        self.brain_id = f"brain-{name}-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.config = config or {}
        self.neural = NeuralCortex(dimension)
        self.symbolic = SymbolicCortex()
        self.decisions = 0
        self.memory_graph: Dict[str, MemoryNode] = {}
        self.recent_states: List[CognitiveState] = []
        logger.info("DualBrain initialized: %s", self.brain_id)

    def think(self, prompt: str, context: Optional[Dict] = None) -> str:
        self.decisions += 1
        vec = self.neural.encode(prompt)
        state = CognitiveState(vector=vec, symbolic_tags=self._extract_tags(prompt), metadata={"context": context or {}})
        self.recent_states.append(state)
        if len(self.recent_states) > 100:
            self.recent_states = self.recent_states[-50:]
        neural_action, confidence = self.neural.decide(vec)
        symbolic_result = self.symbolic.infer(prompt)
        if neural_action == "exploit" and symbolic_result:
            return f"[EXPERT] {symbolic_result} (confidence={confidence:.2f})"
        elif neural_action == "reason":
            reasoning = self._chain_reasoning(prompt, vec)
            return f"[REASON] {reasoning} (confidence={confidence:.2f})"
        return f"[EXPLORE] Analyzing new pattern: {prompt[:80]}... (confidence={confidence:.2f})"

    def decide(self, state_vector: Optional[List[float]] = None, reasoning_level: str = "dual") -> Dict[str, Any]:
        if state_vector is None:
            state_vector = [0.0] * self.neural.dimension
        action, confidence = self.neural.decide(state_vector)
        return {"action": action, "confidence": confidence, "reasoning": reasoning_level, "brain_id": self.brain_id}

    def learn(self, state_vector: List[float], action: str, reward: float, next_state: List[float]):
        state = CognitiveState(vector=state_vector, symbolic_tags=[action])
        self.neural.learn(state, reward)
        self.symbolic.add_fact(f"action_{action}_{int(time.time())}", reward, certainty=abs(reward))

    def remember(self, key: str, value: Any, embedding: Optional[List[float]] = None):
        node_id = hashlib.md5(f"{key}:{time.time()}".encode()).hexdigest()[:16]
        if embedding is None:
            embedding = self.neural.encode(str(value))
        node = MemoryNode(id=node_id, content=str(value), embedding=embedding, node_type="fact", metadata={"key": key})
        self.memory_graph[node_id] = node
        for other in self.memory_graph.values():
            if other.id != node_id:
                sim = self._cosine_sim(embedding, other.embedding)
                if sim > 0.8:
                    node.edges[other.id] = sim
                    other.edges[node_id] = sim
        return node_id

    def search_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        qvec = self.neural.encode(query)
        scored = []
        for node in self.memory_graph.values():
            sim = self._cosine_sim(qvec, node.embedding)
            scored.append((sim, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": n.id, "content": n.content, "similarity": s, "type": n.node_type, "metadata": n.metadata} for s, n in scored[:top_k]]

    def get_state(self) -> Dict[str, Any]:
        return {"brain_id": self.brain_id, "name": self.name, "decisions": self.decisions,
                "neural": self.neural.get_state(), "symbolic": self.symbolic.get_state(), "memory_nodes": len(self.memory_graph)}

    def _extract_tags(self, text: str) -> List[str]:
        tags = []
        for kw in ["scan", "exploit", "payload", "recon", "web", "crypto", "hash", "shell", "network"]:
            if kw in text.lower():
                tags.append(kw)
        return tags

    def _chain_reasoning(self, prompt: str, vec: List[float]) -> str:
        hops = []
        current = self.neural.encode(prompt)
        for _ in range(3):
            best, best_sim = None, 0.0
            for node in self.memory_graph.values():
                sim = self._cosine_sim(current, node.embedding)
                if sim > best_sim:
                    best_sim = sim
                    best = node
            if best and best_sim > 0.6:
                hops.append(best.content[:100])
                current = best.embedding
            else:
                break
        return " -> ".join(hops) if hops else "No prior knowledge chain"

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

