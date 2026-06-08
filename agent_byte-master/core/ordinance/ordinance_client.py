"""
OrdinanceClient
================

The real client that the auto-generated AGENT.md snippets reference.
Any agent — or any Python script — can use this to query the central
neural backend without knowing the internals.

```python
from core.ordinance.ordinance_client import OrdinanceClient

client = OrdinanceClient()
ctx    = client.get_folder_context("core/pipeline")
hits   = client.search("block encoder reed-solomon")
nbs    = client.get_neighbours("a1b2c3d4")   # agent_id
```
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

# CentralNeuralBackend imported lazily in __init__ to avoid circular deps


class OrdinanceClient:
    """
    Read-only query interface to the central neural backend.
    Safe to instantiate multiple times — backend is loaded from disk.
    """

    def __init__(self, root_dir: Optional[str] = None):
        try:
            from core.ordinance.central_backend import CentralNeuralBackend
            self._backend = CentralNeuralBackend(root_dir or os.getcwd())
        except Exception:
            import importlib.util
            p = __import__("pathlib").Path(__file__).resolve().parent / "central_backend.py"
            spec = importlib.util.spec_from_file_location("_cb", p)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            self._backend = m.CentralNeuralBackend(root_dir or os.getcwd())

    # ── folder context ────────────────────────────────────────────────────────

    def get_folder_context(self, folder: str) -> Dict[str, dict]:
        """
        Return all indexed files under `folder`.
        Keys are relative paths; values are file metadata dicts.

        Example
        -------
        >>> ctx = client.get_folder_context("core/pipeline")
        >>> for path, meta in ctx.items():
        ...     print(path, meta["size"], meta["modified"])
        """
        abs_folder = (folder if os.path.isabs(folder)
                      else os.path.join(self._backend.root_dir, folder))
        return self._backend.get_folder_context(abs_folder)

    # ── search ────────────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> List[dict]:
        """
        Full-text search across all indexed files.
        Uses KnowledgeTank FTS5 when available, path substring otherwise.

        Example
        -------
        >>> results = client.search("crystal lattice pipeline")
        >>> for r in results:
        ...     print(r["path"])
        """
        return self._backend.search(query, limit=limit)

    # ── agent/graph queries ───────────────────────────────────────────────────

    def get_neighbours(self, agent_id: str, radius: int = 2) -> List[dict]:
        """
        Return folder agents connected to agent_id in the NeuroGraph.
        Useful for understanding which folders depend on each other.

        Example
        -------
        >>> nbs = client.get_neighbours("a1b2c3d4")
        >>> for nb in nbs:
        ...     print(nb["folder"])
        """
        ng = self._backend._ng
        if not ng:
            return []
        try:
            ctx = ng.get_context(f"agent:{agent_id}", radius=radius, kinds=["agent"])
            return [
                {"agent_id": nid.replace("agent:", ""), **data}
                for nid, data in ctx.items()
            ]
        except Exception:
            return []

    def list_agents(self) -> List[dict]:
        """List all registered folder agents."""
        root = self._backend.root_dir
        return [
            {
                "agent_id": aid,
                "folder":   os.path.relpath(info["folder"], root),
                "updated":  info.get("last_updated", "")[:19],
            }
            for aid, info in self._backend.agent_registry.items()
        ]

    def stats(self) -> dict:
        """Overall system statistics."""
        return self._backend.stats()
