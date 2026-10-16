"""Minimal SQLite thought storage backend used by the ThoughtStore adapter.

Stand-in with the same narrow surface the adapter needs (append, get, link,
roots, tree, delta); any object exposing these methods can replace it.
"""
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class ThoughtStore:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS thoughts (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    root_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent_id TEXT,
                    task_id TEXT,
                    metadata TEXT NOT NULL,
                    created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS links (
                    cause_id TEXT NOT NULL,
                    effect_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    PRIMARY KEY (cause_id, effect_id, relation)
                );
                CREATE INDEX IF NOT EXISTS idx_thoughts_root ON thoughts(root_id);
                CREATE INDEX IF NOT EXISTS idx_links_cause ON links(cause_id);
                """
            )

    @staticmethod
    def _row(row: sqlite3.Row) -> Dict[str, Any]:
        record = dict(row)
        record["metadata"] = json.loads(record["metadata"])
        return record

    def append(self, kind: str, content: str, *, root_id: Optional[str] = None,
               agent_id: Optional[str] = None, task_id: Optional[str] = None,
               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        thought_id = f"th-{uuid.uuid4().hex}"
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO thoughts (id, root_id, kind, content, agent_id, task_id, metadata, created)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (thought_id, root_id or thought_id, kind, content, agent_id, task_id,
                 json.dumps(metadata or {}, default=str), time.time()),
            )
        return self.get(thought_id)

    def get(self, thought_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._db.execute("SELECT * FROM thoughts WHERE id = ?", (thought_id,)).fetchone()
        return self._row(row) if row else None

    def link(self, cause_id: str, effect_id: str, relation: str = "caused") -> bool:
        if self.get(cause_id) is None or self.get(effect_id) is None:
            return False
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO links (cause_id, effect_id, relation) VALUES (?, ?, ?)",
                (cause_id, effect_id, relation),
            )
        return True

    def roots(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM thoughts WHERE id = root_id ORDER BY seq DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row(r) for r in rows]

    def tree(self, root_id: str) -> Optional[Dict[str, Any]]:
        """Return the root's thoughts ordered by seq plus the links between them."""
        if self.get(root_id) is None:
            return None
        with self._lock:
            thoughts = self._db.execute(
                "SELECT * FROM thoughts WHERE root_id = ? ORDER BY seq", (root_id,)
            ).fetchall()
            links = self._db.execute(
                "SELECT l.cause_id, l.effect_id, l.relation FROM links l"
                " JOIN thoughts t ON t.id = l.cause_id WHERE t.root_id = ?", (root_id,)
            ).fetchall()
        return {"root_id": root_id, "thoughts": [self._row(t) for t in thoughts],
                "links": [dict(link) for link in links]}

    def delta(self, since_seq: int = 0, limit: int = 500) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM thoughts WHERE seq > ? ORDER BY seq LIMIT ?", (since_seq, limit)
            ).fetchall()
        return [self._row(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._db.close()
