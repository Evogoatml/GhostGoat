"""GhostGoat Networked Memory — Short-term + Long-term semantic memory."""
import json, time, logging
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ShortTermMemory:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self.store[key] = {"value": value, "expire_at": time.time() + ttl if ttl else None}
    def get(self, key: str) -> Optional[Any]:
        entry = self.store.get(key)
        if not entry: return None
        if entry.get("expire_at") and time.time() > entry["expire_at"]:
            del self.store[key]; return None
        return entry["value"]
    def delete(self, key: str): self.store.pop(key, None)
    def keys(self, pattern: str = "*") -> List[str]:
        return list(self.store.keys()) if pattern == "*" else [k for k in self.store if pattern in k]
    def clear_expired(self):
        now = time.time()
        for k in [k for k, v in self.store.items() if v.get("expire_at") and now > v["expire_at"]]:
            del self.store[k]

class LongTermMemory:
    def __init__(self, storage_path: Optional[str] = None, embedding_dim: int = 128):
        self.storage_path = Path(storage_path or Path.home() / ".ghostgoat" / "long_term_memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim
        self.entries: List[Dict[str, Any]] = []
        self._load()
    def add(self, text: str, embedding: Optional[List[float]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        if embedding is None: embedding = self._hash_embed(text)
        entry = {"id": f"mem-{len(self.entries)}-{int(time.time())}", "text": text, "embedding": embedding,
                 "metadata": metadata or {}, "timestamp": time.time()}
        self.entries.append(entry); self._persist()
        return entry["id"]
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        scored = [(self._cosine_sim(query_embedding, e["embedding"]), e) for e in self.entries if e.get("embedding")]
        scored.sort(reverse=True)
        return [{"id": e["id"], "text": e["text"], "similarity": sim, "metadata": e.get("metadata")} for sim, e in scored[:top_k]]
    def retrieve_by_text(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.search(self._hash_embed(query), top_k)
    def _hash_embed(self, text: str) -> List[float]:
        import hashlib
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = []
        for i in range(self.embedding_dim):
            chunk = h[(i * 2) % len(h): ((i * 2) + 2) % len(h) + 1]
            vec.append(int(chunk, 16) / 255.0 if chunk else 0.5)
        return vec
    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5; nb = sum(x * x for x in b) ** 0.5
        if na == 0 or nb == 0: return 0.0
        return dot / (na * nb)
    def _persist(self):
        try:
            with open(self.storage_path / "memory.jsonl", "w", encoding="utf-8") as f:
                for e in self.entries: f.write(json.dumps(e, default=str) + "\n")
        except Exception as e: logger.warning("Persist failed: %s", e)
    def _load(self):
        path = self.storage_path / "memory.jsonl"
        if not path.exists(): return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip(): self.entries.append(json.loads(line))
        except Exception as e: logger.warning("Load failed: %s", e)

class NetworkedMemory:
    def __init__(self, storage_path: Optional[str] = None):
        self.short = ShortTermMemory(); self.long = LongTermMemory(storage_path=storage_path)
        logger.info("NetworkedMemory initialized")
    def remember(self, text: str, context: Optional[Dict] = None, persist: bool = True):
        if persist: return self.long.add(text, metadata=context)
        key = f"transient-{int(time.time() * 1000)}"
        self.short.set(key, {"text": text, "context": context}, ttl=300)
        return key
    def recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.long.retrieve_by_text(query, top_k)
    def get_transient(self, key: str) -> Optional[Any]: return self.short.get(key)
    def set_transient(self, key: str, value: Any, ttl: int = 300): self.short.set(key, value, ttl=ttl)
    def stats(self) -> Dict[str, Any]: return {"short_term_keys": len(self.short.store), "long_term_entries": len(self.long.entries)}

