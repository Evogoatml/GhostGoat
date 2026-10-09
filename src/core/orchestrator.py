import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from src.memory.base import LearningStrategy, MemoryBackend, MemoryEntry

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.json"


class SIOrchestrator:
    def __init__(self, config_path: Optional[str] = None):
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        if not path.is_file():
            raise FileNotFoundError(f"Config not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.memory_backends: Dict[str, MemoryBackend] = {}
        self.learning_strategies: List[LearningStrategy] = []
        self.memory: Optional[MemoryBackend] = None
        self.dimensions: int = int(self.config.get("memory", {}).get("dimensions", 512))
        self._initialize_memory()

    def _initialize_memory(self) -> None:
        backend_type = self.config.get("memory", {}).get("backend", "hopfield")
        if backend_type == "hopfield":
            from src.memory.hopfield_backend import HopfieldMemory

            self.memory = HopfieldMemory(dimensions=self.dimensions)
            self.register_memory_backend("hopfield", self.memory)
        else:
            raise ValueError(f"Unsupported memory backend: {backend_type}")

    def register_memory_backend(self, name: str, backend: MemoryBackend) -> None:
        self.memory_backends[name] = backend

    def register_learning_strategy(self, strategy: LearningStrategy) -> None:
        self.learning_strategies.append(strategy)

    def _simple_embedding(self, text: str) -> List[float]:
        """Deterministic placeholder embedding (not semantic)."""
        vec = np.zeros(self.dimensions, dtype=float)
        for i, ch in enumerate(text[: self.dimensions]):
            vec[i] = (ord(ch) % 97) / 97.0
        return vec.tolist()

    def store_memory(
        self,
        key: str,
        data: Dict[str, Any],
        embedding: Optional[List[float]] = None,
    ) -> bool:
        if embedding is None:
            embedding = self._simple_embedding(key + " " + json.dumps(data, sort_keys=True))
        if len(embedding) != self.dimensions:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimensions}, got {len(embedding)}"
            )
        return self.memory.store(MemoryEntry(key=key, data=data, embedding=embedding))

    def recall_memory(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        return self.memory.recall(self._simple_embedding(query), top_k)

    def learn_from_experience(self, experiences: List[Dict[str, Any]]) -> None:
        for strategy in self.learning_strategies:
            strategy.learn(experiences)
