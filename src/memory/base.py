from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    key: str
    data: Dict[str, Any]
    embedding: List[float]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryBackend(ABC):
    @abstractmethod
    def store(self, entry: MemoryEntry) -> bool:
        """Store an entry."""

    @abstractmethod
    def recall(self, query_embedding: List[float], top_k: int = 5) -> List[MemoryEntry]:
        """Return the top_k entries most similar to the query."""


class LearningStrategy(ABC):
    @abstractmethod
    def learn(self, experiences: List[Dict[str, Any]]) -> bool:
        """Learn from a batch of experiences."""
