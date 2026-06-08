"""GhostGoat KnowledgeTank — Massive Knowledge Store with GraphRAG Integration."""
import os, json, time, logging
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeEntry:
    id: str
    category: str
    content: str
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    source: str = "unknown"
    confidence: float = 1.0
    usage_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class KnowledgeTank:
    def __init__(self, storage_path: Optional[str] = None, max_entries: int = 100_000):
        self.storage_path = Path(storage_path or Path.home() / ".ghostgoat" / "knowledge_tank")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self.entries: Dict[str, KnowledgeEntry] = {}
        self.index_by_tag: Dict[str, Set[str]] = {}
        self.index_by_category: Dict[str, Set[str]] = {}
        self.total_algorithms = 0
        self._load()
        logger.info("KnowledgeTank loaded: %d entries", len(self.entries))

    def ingest(self, content: str, category: str = "fact", tags: Optional[List[str]] = None,
               source: str = "unknown", embedding: Optional[List[float]] = None,
               metadata: Optional[Dict[str, Any]] = None) -> str:
        entry_id = f"{category}-{int(time.time() * 1000)}-{len(self.entries)}"
        entry = KnowledgeEntry(id=entry_id, category=category, content=content, tags=tags or [],
                               embedding=embedding, source=source, metadata=metadata or {})
        self.entries[entry_id] = entry
        self._index(entry)
        if category == "algorithm":
            self.total_algorithms += 1
        if len(self.entries) > self.max_entries:
            self._prune_oldest()
        return entry_id

    def ingest_bulk(self, items: List[Dict[str, Any]]) -> List[str]:
        ids = [self.ingest(**item) for item in items]
        self._persist()
        return ids

    def search(self, query: str, category: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for entry in self.entries.values():
            if category and entry.category != category:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            score = 0.0
            if query_lower in entry.content.lower(): score += 2.0
            if query_lower in " ".join(entry.tags).lower(): score += 1.5
            if entry.category in query_lower: score += 0.5
            if score > 0:
                entry.usage_count += 1
                entry.last_accessed = time.time()
                results.append((score, entry))
        results.sort(key=lambda x: (-x[0], -x[1].usage_count))
        return [{"id": e.id, "category": e.category, "content": e.content, "tags": e.tags,
                 "source": e.source, "confidence": e.confidence, "usage": e.usage_count} for _, e in results[:limit]]

    def semantic_search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        scored = []
        for entry in self.entries.values():
            if entry.embedding:
                sim = self._cosine_sim(query_embedding, entry.embedding)
                if sim > 0.5:
                    scored.append((sim, entry))
        scored.sort(reverse=True)
        return [{"id": e["id"], "category": e.category, "content": e.content[:500], "similarity": s} for s, e in scored[:top_k]]

    def get_algorithm(self, name: str) -> Optional[Dict[str, Any]]:
        for entry in self.entries.values():
            if entry.category == "algorithm" and name.lower() in entry.content.lower():
                entry.usage_count += 1
                return {"id": entry.id, "content": entry.content, "metadata": entry.metadata}
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {"total_entries": len(self.entries), "total_algorithms": self.total_algorithms,
                "categories": {cat: len(ids) for cat, ids in self.index_by_category.items()},
                "tags": {tag: len(ids) for tag, ids in self.index_by_tag.items()},
                "storage_path": str(self.storage_path)}

    def _index(self, entry: KnowledgeEntry):
        self.index_by_category.setdefault(entry.category, set()).add(entry.id)
        for tag in entry.tags:
            self.index_by_tag.setdefault(tag, set()).add(entry.id)

    def _prune_oldest(self, n: int = 100):
        sorted_entries = sorted(self.entries.values(), key=lambda e: (e.usage_count, e.last_accessed))
        for old in sorted_entries[:n]:
            del self.entries[old.id]
            self.index_by_category.get(old.category, set()).discard(old.id)
            for tag in old.tags:
                self.index_by_tag.get(tag, set()).discard(old.id)
        logger.info("Pruned %d old entries", n)

    def _load(self):
        data_file = self.storage_path / "tank.jsonl"
        if not data_file.exists(): return
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        entry = KnowledgeEntry(**obj)
                        self.entries[entry.id] = entry
                        self._index(entry)
        except Exception as e:
            logger.warning("Failed to load tank: %s", e)

    def _persist(self):
        try:
            with open(self.storage_path / "tank.jsonl", "w", encoding="utf-8") as f:
                for entry in self.entries.values():
                    f.write(json.dumps(entry.__dict__, default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to persist tank: %s", e)

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0: return 0.0
        return dot / (norm_a * norm_b)

