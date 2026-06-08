"""Knowledge accessor for GhostGoat.

Provides a simple ``query`` function that lazily loads a persisted GraphRAG
index (pickle) and returns the top‑k most relevant chunks for a given query.
The heavy‑lifting – building the graph and embedding files – lives in
``brain/agents/holographic_node_graph_rag.py``.  This module is intentionally
lightweight so it can be imported at runtime without pulling in large
dependencies.
"""

import os
import pathlib
import pickle
import logging
from typing import List, Tuple

log = logging.getLogger(__name__)

# Path to the persisted pickle – can be overridden via env var.
_INDEX_PATH = pathlib.Path(
    os.getenv("GRAPH_RAG_INDEX", "./brain/agent_byte-master/knowledge/graph_rag_index.pkl")
).expanduser().resolve()

_store = None  # type: ignore

def _load_store():
    global _store
    if _store is None:
        if _INDEX_PATH.is_file():
            log.info("Loading persisted GraphRAG index from %s", _INDEX_PATH)
            with _INDEX_PATH.open("rb") as f:
                _store = pickle.load(f)  # noqa: S301 – trusted internal data
        else:
            log.info("No persisted GraphRAG index - trying core module")
            try:
                from brain.memory.rag.holographic_node_graph_rag import GraphRAGStore
                _store = GraphRAGStore()
                _store.build_from_path()
            except ImportError:
                log.warning("GraphRAGStore not available, using empty knowledge")
                _store = None
    return _store


def query(query: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Return the most relevant knowledge chunks for ``query``.

    The return value is a list of ``(chunk_text, score)`` tuples ordered by
    descending relevance.
    """
    store = _load_store()
    return store.query(query, top_k=top_k)


def persist():
    """Serialise the current store to disk – useful for a cron job."""
    global _store
    if _store is None:
        log.warning("persist() called before any store was built – nothing to do")
        return
    _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _INDEX_PATH.open("wb") as f:
        pickle.dump(_store, f)  # noqa: S301
    log.info("GraphRAG index persisted to %s", _INDEX_PATH)
