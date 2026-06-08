"""Legacy ragflow package wrapper

The original `memory.rag.ragflow` directory contains a full web UI and SDK for the RagFlow service.
It is **not** needed for the core GhostGoat engine, and importing it pulls in a large
dependency tree (FastAPI, React, many test fixtures).  Keeping it in the import path
causes accidental imports, namespace collisions and slower start‑up.

This thin wrapper makes the intention explicit:
* Any code that does `from memory.rag import ragflow` will receive a **DeprecationWarning**.
* The core GraphRAG implementation (`Neo4jGraphRAG`) is re‑exported for backwards‑compatible use.
* If a developer really needs the full UI they can still import it via the original
  path `memory.rag.ragflow` – this wrapper does **not** delete those files.
"""

import warnings
warnings.warn(
    "`memory.rag.ragflow` is deprecated – use the lightweight Neo4jGraphRAG from `memory.graphrag`.",
    DeprecationWarning,
    stacklevel=2,
)

# Re‑export the primary GraphRAG class so existing code that expects
# `memory.rag.Neo4jGraphRAG` continues to work.
from ..graphrag import Neo4jGraphRAG  # noqa: F401

# Optional convenience alias if some legacy code imports the submodule directly.
# Users can still do `import memory.rag.ragflow` but will get the same warning.

__all__ = ["Neo4jGraphRAG"]
