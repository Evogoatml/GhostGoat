"""GhostGoat GraphRAG Engine — Semantic Vector Graph with Typed Nodes and Edges."""
import json, time, uuid, hashlib, logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class GraphNode:
    id: str
    label: str
    node_type: str
    content: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=time.time)

@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class GraphRAGEngine:
    def __init__(self, storage_path: Optional[str] = None, embedding_dim: int = 128):
        self.storage_path = Path(storage_path or Path.home() / ".ghostgoat" / "graphrag")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, List[Tuple[str, float, str]]] = {}
        self._load()
        logger.info("GraphRAGEngine ready: %d nodes, %d edges", len(self.nodes), len(self.edges))

    def add_node(self, label: str, content: str, node_type: str, vector: Optional[List[float]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> str:
        nid = f"{node_type.lower()}-{uuid.uuid4().hex[:8]}"
        if vector is None:
            vector = self._deterministic_embed(content)
        node = GraphNode(id=nid, label=label, node_type=node_type, content=content,
                         vector=vector, metadata=metadata or {})
        self.nodes[nid] = node
        self.adjacency[nid] = []
        self._auto_link(node)
        self._persist()
        return nid

    def add_edge(self, source: str, target: str, edge_type: str, weight: float = 1.0,
                 metadata: Optional[Dict[str, Any]] = None):
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("Source or target node not found")
        edge = GraphEdge(source=source, target=target, edge_type=edge_type, weight=weight, metadata=metadata or {})
        self.edges.append(edge)
        self.adjacency[source].append((target, weight, edge_type))
        self._persist()

    def search(self, query_vector: List[float], node_type: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        scored = []
        for node in self.nodes.values():
            if node_type and node.node_type != node_type: continue
            sim = self._cosine_sim(query_vector, node.vector)
            scored.append((sim, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": n.id, "label": n.label, "type": n.node_type, "content": n.content[:300],
                 "similarity": sim, "metadata": n.metadata} for sim, n in scored[:top_k]]

    def traverse(self, start_node_id: str, depth: int = 2, edge_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        visited, results, frontier = set(), [], [(start_node_id, 0)]
        while frontier:
            current_id, dist = frontier.pop(0)
            if current_id in visited or dist > depth: continue
            visited.add(current_id)
            if current_id in self.nodes:
                node = self.nodes[current_id]
                results.append({"id": node.id, "label": node.label, "type": node.node_type,
                                "content": node.content[:200], "depth": dist})
            for target, weight, etype in self.adjacency.get(current_id, []):
                if edge_types and etype not in edge_types: continue
                frontier.append((target, dist + 1))
        return results

    def query_context(self, prompt: str, max_tokens: int = 2000) -> str:
        qvec = self._deterministic_embed(prompt)
        hits = self.search(qvec, top_k=5)
        parts, total = [], 0
        max_chars = max_tokens * 4
        for hit in hits:
            text = f"[{hit['type']}] {hit['label']}: {hit['content']}"
            if total + len(text) > max_chars: break
            parts.append(text); total += len(text)
        return "\n\n---\n\n".join(parts)

    def get_subgraph(self, center_id: str, radius: int = 1) -> Dict[str, Any]:
        if center_id not in self.nodes: return {"nodes": [], "edges": []}
        node_ids = {center_id}
        edge_subset = []
        for _ in range(radius):
            new_ids = set()
            for edge in self.edges:
                if edge.source in node_ids:
                    new_ids.add(edge.target); edge_subset.append(edge)
                elif edge.target in node_ids:
                    new_ids.add(edge.source); edge_subset.append(edge)
            node_ids.update(new_ids)
        return {"nodes": [self.nodes[nid].__dict__ for nid in node_ids if nid in self.nodes],
                "edges": [e.__dict__ for e in edge_subset]}

    def get_stats(self) -> Dict[str, Any]:
        return {"nodes": len(self.nodes), "edges": len(self.edges),
                "node_types": {n.node_type for n in self.nodes.values()},
                "edge_types": {e.edge_type for e in self.edges}}

    def _auto_link(self, new_node: GraphNode, threshold: float = 0.85):
        for node in self.nodes.values():
            if node.id == new_node.id: continue
            sim = self._cosine_sim(new_node.vector, node.vector)
            if sim > threshold:
                self.edges.append(GraphEdge(source=new_node.id, target=node.id, edge_type="SIMILAR_TO", weight=sim))
                self.adjacency.setdefault(new_node.id, []).append((node.id, sim, "SIMILAR_TO"))
                self.adjacency.setdefault(node.id, []).append((new_node.id, sim, "SIMILAR_TO"))

    def _deterministic_embed(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = []
        for i in range(self.embedding_dim):
            chunk = h[(i * 2) % len(h): ((i * 2) + 2) % len(h) + 1]
            val = int(chunk, 16) / 255.0 if chunk else 0.5
            vec.append(val)
        return vec

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0: return 0.0
        return dot / (norm_a * norm_b)

    def _persist(self):
        try:
            data = {"nodes": {nid: n.__dict__ for nid, n in self.nodes.items()}, "edges": [e.__dict__ for e in self.edges]}
            with open(self.storage_path / "graph.json", "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            logger.warning("Graph persist failed: %s", e)

    def _load(self):
        path = self.storage_path / "graph.json"
        if not path.exists(): return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for nid, obj in data.get("nodes", {}).items():
                self.nodes[nid] = GraphNode(**obj)
            for obj in data.get("edges", []):
                e = GraphEdge(**obj)
                self.edges.append(e)
                self.adjacency.setdefault(e.source, []).append((e.target, e.weight, e.edge_type))
            logger.info("Graph loaded: %d nodes, %d edges", len(self.nodes), len(self.edges))
        except Exception as e:
            logger.warning("Graph load failed: %s", e)

