"""GhostGoat Budget & Cache — Token cost tracking + semantic response cache."""
import json, time, logging, sqlite3, hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from core.embed_service import embed, cosine_similarity

logger = logging.getLogger(__name__)

class SemanticCache:
    def __init__(self, db_path: Optional[str] = None, similarity_threshold: float = 0.92, ttl_seconds: int = 3600):
        self.threshold = similarity_threshold
        self.ttl = ttl_seconds
        self.path = Path(db_path or Path.home() / ".ghostgoat" / "semantic_cache.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.path)) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    id INTEGER PRIMARY KEY,
                    query_hash TEXT,
                    embedding TEXT,
                    response TEXT,
                    model TEXT,
                    tokens_in INT,
                    tokens_out INT,
                    timestamp REAL
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_ts ON cache(timestamp)")

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def get(self, query: str, model: str) -> Optional[Dict[str, Any]]:
        cutoff = time.time() - self.ttl
        with sqlite3.connect(str(self.path)) as c:
            rows = c.execute(
                "SELECT embedding, response, tokens_in, tokens_out, timestamp FROM cache WHERE model=? AND timestamp>?",
                (model, cutoff)
            ).fetchall()
        qemb = embed(query)
        best_sim, best_response = 0.0, None
        for emb_str, resp, ti, to, ts in rows:
            emb = json.loads(emb_str)
            sim = cosine_similarity(qemb, emb)
            if sim > best_sim:
                best_sim = sim
                best_response = {"response": resp, "tokens_in": ti, "tokens_out": to, "cached": True, "similarity": round(sim, 3)}
        if best_sim >= self.threshold:
            logger.info("Cache hit (sim=%.3f)", best_sim)
            return best_response
        return None

    def put(self, query: str, model: str, response: str, tokens_in: int = 0, tokens_out: int = 0):
        with sqlite3.connect(str(self.path)) as c:
            c.execute(
                "INSERT INTO cache (query_hash, embedding, response, model, tokens_in, tokens_out, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self._hash(query), json.dumps(embed(query)), response, model, tokens_in, tokens_out, time.time())
            )
            c.commit()

    def prune(self, max_entries: int = 10000):
        with sqlite3.connect(str(self.path)) as c:
            count = c.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            if count > max_entries:
                c.execute("DELETE FROM cache WHERE id IN (SELECT id FROM cache ORDER BY timestamp ASC LIMIT ?)", (count - max_entries,))
                c.commit()

class CostBudget:
    MODEL_COSTS = {
        "gpt-4o": {"in": 0.005, "out": 0.015},
        "claude-3-5-sonnet": {"in": 0.003, "out": 0.015},
        "llama3.2": {"in": 0.0, "out": 0.0},
        "mistral-small": {"in": 0.0, "out": 0.0},
    }

    def __init__(self, session_id: str = "default", budget_usd: float = 10.0):
        self.session_id = session_id
        self.budget = budget_usd
        self.spent = 0.0
        self.calls = 0
        self.history: List[Dict[str, Any]] = []

    def charge(self, model: str, tokens_in: int, tokens_out: int) -> bool:
        rates = self.MODEL_COSTS.get(model, {"in": 0.0, "out": 0.0})
        cost = (tokens_in / 1000.0) * rates["in"] + (tokens_out / 1000.0) * rates["out"]
        if self.spent + cost > self.budget:
            logger.warning("Budget exceeded: spent=$%.4f / $%.4f", self.spent, self.budget)
            return False
        self.spent += cost
        self.calls += 1
        self.history.append({"model": model, "cost": cost, "tokens_in": tokens_in, "tokens_out": tokens_out, "timestamp": time.time()})
        logger.info("Charged $%.6f for %s (%d/%d tokens). Total: $%.4f/$%.4f", cost, model, tokens_in, tokens_out, self.spent, self.budget)
        return True

    def can_afford(self, model: str, estimated_tokens: int = 2000) -> bool:
        rates = self.MODEL_COSTS.get(model, {"in": 0.0, "out": 0.0})
        est = (estimated_tokens / 1000.0) * (rates["in"] + rates["out"])
        return self.spent + est <= self.budget

    def report(self) -> Dict[str, Any]:
        return {"session": self.session_id, "budget": self.budget, "spent": round(self.spent, 6),
                "remaining": round(self.budget - self.spent, 6), "calls": self.calls,
                "by_model": {m: sum(h["cost"] for h in self.history if h["model"] == m) for m in set(h["model"] for h in self.history)}}

