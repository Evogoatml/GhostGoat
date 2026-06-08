"""Simple GraphRAG‑style knowledge store for GhostGoat.

This is a **lightweight** implementation that avoids heavy dependencies:
* It walks a root directory (default ``./brain/agent_byte-master/knowledge``).
* Text files (``.md``, ``.txt``) are read and split into paragraphs (blank‑line
  separated).  Each paragraph becomes a *node*.
* No real vector embeddings are computed – we rely on a very cheap *keyword
  scoring* for relevance: the number of query terms appearing in the chunk.
* The public API mirrors the original ``GraphRAGStore`` used elsewhere in the
  repo: ``build_from_path()``, ``query(query, top_k)`` and ``graph`` (a simple
  ``networkx.DiGraph`` for optional visualisation).

The store is intentionally simple so it can be imported without extra
packages.  If you later want true embeddings you can replace ``_score_chunk``
with a call to the LLM embedder.
"""

import os
import pathlib
import logging
from typing import List, Tuple

log = logging.getLogger(__name__)

try:
    import networkx as nx
except Exception:  # pragma: no cover – networkx is optional
    nx = None


class GraphRAGStore:
    """A minimal knowledge graph for GhostGoat.

    Attributes
    ----------
    graph : nx.DiGraph | None
        Optional directed graph where each node is a text chunk.
    _chunks : List[str]
        Flat list of all loaded paragraphs.
    """

    def __init__(self, root_path: str | None = None):
        self.root = pathlib.Path(root_path or "./brain/agent_byte-master/knowledge").expanduser().resolve()
        self.graph = nx.DiGraph() if nx else None
        self._chunks: List[str] = []

    # ------------------------------------------------------------------
    def _load_files(self) -> None:
        """Populate ``self._chunks`` from all ``.md``/``.txt`` files under ``self.root``.
        """
        if not self.root.is_dir():
            log.warning("GraphRAG root path does not exist: %s", self.root)
            return
        for file_path in self.root.rglob("*.*"):
            if file_path.suffix.lower() not in {".md", ".txt", ".json", ".yaml", ".yml"}:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:  # pragma: no cover
                log.exception("Failed to read %s", file_path)
                continue
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            self._chunks.extend(paragraphs)

    # ------------------------------------------------------------------
    def build_from_path(self) -> None:
        """Public entry‑point used by the Telegram bot.

        Loads files and, if ``networkx`` is available, builds a trivial graph where
        each node points to the next one (preserves ordering).
        """
        log.info("Building GraphRAG store from %s", self.root)
        self._load_files()
        if nx and self.graph is not None:
            for idx, chunk in enumerate(self._chunks):
                node_id = f"n{idx}"
                self.graph.add_node(node_id, text=chunk)
                if idx > 0:
                    self.graph.add_edge(f"n{idx-1}", node_id)
        log.info("GraphRAG store ready – %d chunks loaded", len(self._chunks))

    # ------------------------------------------------------------------
    @staticmethod
    def _score_chunk(chunk: str, query: str) -> int:
        """Very cheap relevance: count of query words appearing in the chunk."""
        q_terms = set(query.lower().split())
        c_terms = set(chunk.lower().split())
        return len(q_terms & c_terms)

    # ------------------------------------------------------------------
    def query(self, query: str, top_k: int = 5) -> List[Tuple[str, int]]:
        """Return the *top_k* most relevant chunks for ``query``.

        Returns a list of ``(chunk_text, score)`` tuples ordered by descending
        score.  Zero‑score results are filtered out.
        """
        if not self._chunks:
            log.warning("GraphRAG query called before any data was loaded")
            return []
        scored = [(chunk, self._score_chunk(chunk, query)) for chunk in self._chunks]
        scored.sort(key=lambda x: x[1], reverse=True)
        filtered = [(c, s) for c, s in scored if s > 0]
        return filtered[:top_k]

    # ------------------------------------------------------------------
    def nodes(self):
        """Helper for debugging – return number of nodes in the graph (if any)."""
        if self.graph:
            return self.graph.nodes()
        return []
