"""GhostGoat State Persistence — SQLite checkpoints + session recovery."""
import json, sqlite3, pickle, logging, time, os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StateCheckpoint:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or Path.home() / ".ghostgoat" / "checkpoints.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp REAL,
                    tag TEXT,
                    state BLOB,
                    state_hash TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created REAL,
                    last_checkpoint REAL,
                    metadata TEXT
                )
            """)
            conn.commit()

    def save(self, state: Dict[str, Any], session_id: str = "default", tag: str = "auto") -> str:
        ts = time.time()
        blob = pickle.dumps(state)
        h = hash(blob) & 0xFFFFFFFF
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "INSERT INTO checkpoints (session_id, timestamp, tag, state, state_hash) VALUES (?, ?, ?, ?, ?)",
                (session_id, ts, tag, blob, str(h))
            )
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, created, last_checkpoint, metadata) VALUES (?, ?, ?, ?)",
                (session_id, ts, ts, json.dumps({"last_tag": tag, "size_kb": len(blob) // 1024}))
            )
            conn.commit()
        logger.info("Checkpoint saved: session=%s tag=%s id=%d", session_id, tag, cur.lastrowid)
        return f"{session_id}:{cur.lastrowid}"

    def restore(self, session_id: str = "default", tag: Optional[str] = None,
                max_age_seconds: Optional[float] = None) -> Optional[Dict[str, Any]]:
        cutoff = time.time() - max_age_seconds if max_age_seconds else 0
        params = [session_id, cutoff]
        sql = "SELECT state FROM checkpoints WHERE session_id=? AND timestamp>?"
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        sql += " ORDER BY timestamp DESC LIMIT 1"
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
        if row:
            state = pickle.loads(row[0])
            logger.info("Restored checkpoint for %s", session_id)
            return state
        logger.warning("No checkpoint found for %s", session_id)
        return None

    def list_sessions(self) -> Dict[str, Any]:
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = conn.execute("SELECT session_id, created, last_checkpoint, metadata FROM sessions").fetchall()
        return {sid: {"created": c, "last_checkpoint": lc, "metadata": json.loads(m) if m else {}}
                for sid, c, lc, m in rows}

    def prune(self, keep_per_session: int = 10, max_age_days: int = 7):
        cutoff = time.time() - max_age_days * 86400
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM checkpoints WHERE timestamp <?", (cutoff,))
            conn.execute("""
                DELETE FROM checkpoints WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY timestamp DESC) rn
                        FROM checkpoints
                    ) WHERE rn <= ?
                )
            """, (keep_per_session,))
            conn.commit()
        logger.info("Pruned old checkpoints")

