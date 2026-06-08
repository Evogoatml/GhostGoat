"""
MemoryController — unified memory access for all agents.
Wraps ChromaDB (vector), DuckDB (structured), and the existing
SemanticKnowledgeTank so every agent reads/writes through one interface.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryController:
    """Single memory interface for the whole system."""

    _instance: Optional["MemoryController"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    def __init__(self, chroma_dir: str = "./chroma_db", db_path: str = "./agent.duckdb"):
        if self._ready:
            return
        self.chroma_dir = chroma_dir
        self.db_path = db_path
        self._vector: Any = None
        self._db: Any = None
        self._ready = True

    # ── lazy init ─────────────────────────────────────────────────────────────

    def _get_vector(self):
        if self._vector is None:
            try:
                from core.brain.agents.meta_godel_agent import LocalVectorStore
                self._vector = LocalVectorStore(self.chroma_dir)
            except Exception as e:
                logger.warning("Vector store unavailable: %s", e)
        return self._vector

    def _get_db(self):
        if self._db is None:
            try:
                import duckdb
                self._db = duckdb.connect(self.db_path)
                self._db.execute("""
                    CREATE TABLE IF NOT EXISTS agent_memory (
                        id VARCHAR, agent_id VARCHAR, content TEXT,
                        metadata VARCHAR, ts TIMESTAMP DEFAULT now()
                    )
                """)
            except Exception as e:
                logger.warning("DuckDB unavailable: %s", e)
        return self._db

    # ── public API ────────────────────────────────────────────────────────────

    def remember(self, content: str, agent_id: str, metadata: Optional[Dict] = None) -> str:
        """Store a memory — goes to both vector store and structured DB."""
        meta = metadata or {}
        doc_id = ""
        vs = self._get_vector()
        if vs:
            try:
                doc_id = vs.add_memory(content, meta, agent_id)
            except Exception as e:
                logger.debug("Vector store write failed: %s", e)
        db = self._get_db()
        if db:
            try:
                db.execute(
                    "INSERT INTO agent_memory (id, agent_id, content, metadata) VALUES (?,?,?,?)",
                    [doc_id or "local", agent_id, content, json.dumps(meta)]
                )
            except Exception as e:
                logger.debug("DuckDB write failed: %s", e)
        return doc_id

    def recall(self, query: str, agent_id: Optional[str] = None, k: int = 5) -> List[Dict]:
        """Semantic recall — returns top-k relevant memories."""
        vs = self._get_vector()
        if vs:
            try:
                return vs.similarity_search(query, k=k, agent_id=agent_id)
            except Exception as e:
                logger.debug("Vector recall failed: %s", e)
        return []

    def query(self, sql: str) -> Any:
        """Run a SQL query against the structured memory DB."""
        db = self._get_db()
        if db:
            try:
                return db.execute(sql).fetchdf()
            except Exception as e:
                logger.warning("SQL query failed: %s", e)
        return None


# Singleton
memory = MemoryController()
