"""Thin GhostGoat adapter over ThoughtStore.

Orchestrator, agents and the API talk only to this class, never to storage
internals. Recording is best-effort: persistence failures are logged and never
break task execution.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ghostgoat.thoughts")


class ThoughtMemory:
    def __init__(self, store: Any):
        self._store = store

    def record(self, kind: str, content: str, *, parent_id: Optional[str] = None,
               agent_id: Optional[str] = None, task_id: Optional[str] = None,
               metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Persist a thought (a root when parent_id is None); return its id or None on failure."""
        try:
            root_id = None
            if parent_id is not None:
                parent = self._store.get(parent_id)
                root_id = parent["root_id"] if parent else None
            thought = self._store.append(kind, content, root_id=root_id, agent_id=agent_id,
                                         task_id=task_id, metadata=metadata)
            if parent_id is not None and root_id is not None:
                self._store.link(parent_id, thought["id"], "caused")
            return thought["id"]
        except Exception:
            logger.exception("Failed to record thought %s", kind)
            return None

    def link(self, cause_id: str, effect_id: str, relation: str = "caused") -> bool:
        return self._store.link(cause_id, effect_id, relation)

    def get(self, thought_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(thought_id)

    def roots(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._store.roots(limit)

    def tree(self, root_id: str) -> Optional[Dict[str, Any]]:
        return self._store.tree(root_id)

    def delta(self, since_seq: int = 0, limit: int = 500) -> List[Dict[str, Any]]:
        return self._store.delta(since_seq, limit)
