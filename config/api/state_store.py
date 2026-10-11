"""SQLite persistence for API task and message records."""

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


class RuntimeState:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv(
            "GHOSTGOAT_STATE_DB", ROOT / ".backend" / "runtime.sqlite3"
        ))
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    record TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    record TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._connection.commit()

    def save_task(self, task: dict[str, Any]) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO tasks (id, record) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET record=excluded.record, "
                "updated_at=CURRENT_TIMESTAMP",
                (task["id"], json.dumps(task)),
            )
            self._connection.commit()

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT record FROM tasks ORDER BY updated_at DESC, rowid DESC"
            ).fetchall()
        return [json.loads(row["record"]) for row in rows]

    def save_message(self, message: dict[str, Any]) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO messages (id, record) VALUES (?, ?)",
                (message["id"], json.dumps(message)),
            )
            self._connection.commit()

    def list_messages(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT record FROM messages ORDER BY rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row["record"]) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._connection.close()
