#!/usr/bin/env python3
"""
Holographic GraphRAG Store
--------------------------
A lightweight GraphRAG implementation that loads the project's
knowledge‑base (JSON, TXT, MD files) and builds a *holographic node* graph
where each node is a semantic vector (embedding) of a chunk of text.
The graph can be queried from any component (e.g. the Telegram bot) via
`GraphRAGStore().query("my question")`.

The implementation is deliberately self‑contained – it uses the local
Ollama model (default ``llama3.2``) for embeddings, stores the graph in a
`networkx.DiGraph`, and connects nodes whose cosine similarity exceeds a
threshold.  This yields a "holographic" structure: each piece of knowledge
is a node that can be traversed via semantic edges.
"""

import os
import json
import hashlib
import pathlib
import time
from typing import List, Dict, Tuple
import requests
import numpy as np
import networkx as nx

# ---------------------------------------------------------------------------
# Helper: simple cosine similarity for float vectors
# ---------------------------------------------------------------------------
def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# ---------------------------------------------------------------------------
# Embedding provider – Ollama local endpoint
# ---------------------------------------------------------------------------
class OllamaEmbedder:
    """Thin wrapper around ``POST /api/embeddings``.

    The default model ``llama3.2`` ships with a 4096‑dimensional embedding
    vector.  If the endpoint is unavailable we fall back to a deterministic
    SHA‑256‑based pseudo‑embedding (good enough for a demo).
    """

    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._fallback = False

    def _request(self, text: str) -> List[float]:
        try:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            # Ollama returns ``embedding`` as a list of floats
            return data.get("embedding", [])
        except Exception as e:
            # fallback – deterministic hash → 128‑dim vector
            self._fallback = True
            h = hashlib.sha256(text.encode()).digest()
            # map bytes (0‑255) to floats in [-1, 1]
            vec = [(b / 127.5) - 1.0 for b in h[:128]]
            return vec

    def embed(self, text: str) -> np.ndarray:
        vec = self._request(text)
        return np.asarray(vec, dtype=np.float32)

# ---------------------------------------------------------------------------
# Core GraphRAG Store
# ---------------------------------------------------------------------------
class GraphRAGStore:
    """Builds a holographic node graph from the repository's knowledge base.

    * Each **node** represents a chunk of text (max ~500 characters).
    * Nodes store ``content`` and the pre‑computed ``embedding``.
    * An **edge** ``(src, dst)`` exists when the cosine similarity between the
      two embeddings exceeds ``edge_threshold`` – the edge weight is that cosine.
    """

    def __init__(self, chunk_size: int = 500, edge_threshold: float = 0.78, root_path: str = None):
        self.chunk_size = chunk_size
        self.edge_threshold = edge_threshold
        self.graph = nx.DiGraph()
        self.embedder = OllamaEmbedder()
        # Cache to avoid re‑embedding unchanged files
        self._file_hash: Dict[str, str] = {}
        # Default knowledge base location – overridden if ``root_path`` supplied
        self.default_root = root_path or "./brain/agent_byte-master/knowledge"

    # ---------------------------------------------------------------------
    # Public API – building the graph
    # ---------------------------------------------------------------------
    def build_from_path(self, root: str = None) -> None:
        """Traverse ``root`` and ingest every ``*.json``/``*.txt``/``*.md`` file.
        """
        root_path = pathlib.Path(root or self.default_root).expanduser().resolve()
        if not root_path.is_dir():
            raise FileNotFoundError(f"Knowledge base directory not found: {root_path}")
        for file_path in root_path.rglob("*.*"):
            if file_path.suffix.lower() not in {".json", ".txt", ".md"}:
                continue
            self._process_file(str(file_path))
        self._connect_similar_nodes()

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _process_file(self, file_path: str) -> None:
        """Read a file, chunk it, embed each chunk and add to the graph.
        ``file_path`` is stored as a node attribute for provenance.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception as exc:
            print(f"[GraphRAG] Could not read {file_path}: {exc}")
            return

        # Simple hash to detect changes – if unchanged we skip re‑embedding
        file_hash = hashlib.sha256(raw.encode()).hexdigest()
        if self._file_hash.get(file_path) == file_hash:
            return  # already processed
        self._file_hash[file_path] = file_hash

        # Normalise JSON → string if needed
        if file_path.lower().endswith('.json'):
            try:
                data = json.loads(raw)
                raw = json.dumps(data, indent=2, ensure_ascii=False)
            except Exception:
                pass

        # Chunking – split by whitespace preserving approx size
        chunks = []
        start = 0
        while start < len(raw):
            end = start + self.chunk_size
            # avoid cutting in the middle of a line if possible
            if end < len(raw):
                nl = raw.rfind('\n', start, end)
                if nl != -1:
                    end = nl
            chunks.append(raw[start:end].strip())
            start = end

        for idx, chunk in enumerate(chunks):
            if not chunk:
                continue
            embed_vec = self.embedder.embed(chunk)
            node_id = f"{file_path}#c{idx}"
            self.graph.add_node(
                node_id,
                content=chunk,
                embedding=embed_vec,
                source=file_path,
                chunk_index=idx,
                type="knowledge",
            )

    def _connect_similar_nodes(self) -> None:
        """Create edges between nodes whose cosine similarity exceeds the threshold.
        This is O(N²) but acceptable for a few thousand nodes (the repo is small).
        """
        nodes = list(self.graph.nodes(data=True))
        for i, (nid_i, data_i) in enumerate(nodes):
            vec_i = np.asarray(data_i["embedding"], dtype=np.float32)
            for nid_j, data_j in nodes[i + 1 :]:
                vec_j = np.asarray(data_j["embedding"], dtype=np.float32)
                sim = _cosine(vec_i, vec_j)
                if sim >= self.edge_threshold:
                    # Undirected semantic relationship – add both directions
                    self.graph.add_edge(nid_i, nid_j, weight=sim)
                    self.graph.add_edge(nid_j, nid_i, weight=sim)

    # ---------------------------------------------------------------------
    # Query API
    # ---------------------------------------------------------------------
    def query(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Return the *top_k* most similar chunks to ``query``.
        The result is a list of ``(content, similarity)`` tuples ordered by
        descending similarity.
        """
        q_vec = self.embedder.embed(query)
        similarities: List[Tuple[str, float]] = []
        for nid, data in self.graph.nodes(data=True):
            node_vec = np.asarray(data["embedding"], dtype=np.float32)
            sim = _cosine(q_vec, node_vec)
            similarities.append((data["content"], sim))
        # Sort and truncate
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    # ---------------------------------------------------------------------
    # Persistence helpers (optional) – dump/load the graph to JSON for quick reload
    # ---------------------------------------------------------------------
    def dump(self, path: str) -> None:
        """Serialise the graph (node attributes only; edges store weight)."""
        data = {
            "nodes": [
                {"id": nid, **{k: v for k, v in attrs.items() if k != "embedding"}}
                for nid, attrs in self.graph.nodes(data=True)
            ],
            "edges": [
                {"src": u, "dst": v, "weight": d.get("weight", 0.0)}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        """Load a previously dumped graph (embeddings are re‑computed on‑fly).
        For a production system you would store embeddings as well, but for the
        demo we recompute them to keep the JSON small.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.graph.clear()
        for n in data.get("nodes", []):
            nid = n.pop("id")
            content = n.get("content", "")
            # recompute embedding
            embed_vec = self.embedder.embed(content)
            n["embedding"] = embed_vec
            self.graph.add_node(nid, **n)
        for e in data.get("edges", []):
            self.graph.add_edge(e["src"], e["dst"], weight=e.get("weight", 0.0))

# ---------------------------------------------------------------------------
# Convenience: build the store on import (useful for quick REPL access)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    store = GraphRAGStore()
    print("[GraphRAG] Building index from ./brain/knowledge_base …")
    store.build_from_path()
    dump_file = "graph_rag_index.json"
    store.dump(dump_file)
    print(f"[GraphRAG] Index saved to {dump_file}. Ready for queries.")
    # Example query loop
    while True:
        q = input("\nQuery (or 'exit'): ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        results = store.query(q, top_k=3)
        print("--- Top results ---")
        for txt, sim in results:
            print(f"[{sim:.3f}] {txt[:200].replace('\n', ' ')}")
            print()
