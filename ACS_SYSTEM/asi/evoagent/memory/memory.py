import os
import sqlite3
import time
from typing import List

from sentence_transformers import SentenceTransformer
import numpy as np


class Memory:
    def __init__(self, db_path="memory/agent.db", model_name="sentence-transformers/all-MiniLM-L6-v2"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS mem (id INTEGER PRIMARY KEY, ts REAL, text TEXT, vec BLOB)"
        )
        self.model = SentenceTransformer(model_name)

    def store_snippet(self, topic: str, thought: str, output: str):
        text = f"{topic}\n{thought}\n{output}"
        vec = self.model.encode([text])[0].astype(np.float32).tobytes()
        self.conn.execute("INSERT INTO mem (ts, text, vec) VALUES (?,?,?)", (time.time(), text, vec))
        self.conn.commit()

    def recall(self, query: str, k: int = 5) -> List[str]:
        # naive in-memory scan for MVP
        cur = self.conn.execute("SELECT id, text, vec FROM mem ORDER BY id DESC LIMIT 200")
        rows = cur.fetchall()
        if not rows:
            return []
        qv = self.model.encode([query])[0].astype(np.float32)

        def score(row):
            v = np.frombuffer(row[2], dtype=np.float32)
            return float(np.dot(v, qv) / (np.linalg.norm(v) * np.linalg.norm(qv) + 1e-9))

        ranked = sorted(rows, key=score, reverse=True)[:k]
        return [r[1] for r in ranked]
