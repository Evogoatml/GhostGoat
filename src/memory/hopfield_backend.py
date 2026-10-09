from typing import Dict, List

import numpy as np

from src.memory.base import MemoryBackend, MemoryEntry


class HopfieldMemory(MemoryBackend):
    def __init__(self, dimensions: int = 512):
        self.dimensions = dimensions
        self.memory_store: Dict[str, MemoryEntry] = {}
        self.weight_matrix = np.zeros((dimensions, dimensions))

    def store(self, entry: MemoryEntry) -> bool:
        if len(entry.embedding) != self.dimensions:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimensions}, got {len(entry.embedding)}"
            )
        self.memory_store[entry.key] = entry
        emb = np.array(entry.embedding, dtype=float)
        self.weight_matrix += np.outer(emb, emb)
        np.fill_diagonal(self.weight_matrix, 0)
        return True

    def recall(self, query_embedding: List[float], top_k: int = 5) -> List[MemoryEntry]:
        if len(query_embedding) != self.dimensions:
            raise ValueError(
                f"Query dimension mismatch: expected {self.dimensions}, got {len(query_embedding)}"
            )
        query = np.array(query_embedding, dtype=float)
        qnorm = np.linalg.norm(query)
        results = []
        for entry in self.memory_store.values():
            emb = np.array(entry.embedding, dtype=float)
            sim = float(np.dot(query, emb) / (qnorm * np.linalg.norm(emb) + 1e-8))
            results.append((sim, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:top_k]]
