"""
Central Neural Backend
=======================

Single source of truth for the Distributed Agent System.
Instead of standalone pickle/json files, this uses GhostGoat's
existing neural stack:

  File Registry  → KnowledgeTank (SQLite + FTS5)
  Knowledge Graph→ NeuroGraph (NetworkX + ChromaDB)
  File hashes    → local .backend/ (fast change detection only)

All folder agents share this one backend.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BACKEND_DIR_NAME = ".backend"


class CentralNeuralBackend:
    """
    Central neural network — single source of truth.
    Delegates heavy storage to GhostGoat's existing systems.
    Maintains a lightweight .backend/ dir for fast file-change detection.
    """

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir    = root_dir or os.getcwd()
        self.backend_dir = os.path.join(self.root_dir, BACKEND_DIR_NAME)
        self._registry_path = os.path.join(self.backend_dir, "file_registry.json")
        self._agents_path   = os.path.join(self.backend_dir, "agents.json")

        # Lightweight in-process caches (backed by files above)
        self.file_registry:  Dict[str, dict] = {}
        self.agent_registry: Dict[str, dict] = {}

        # Heavy storage — GhostGoat neural systems (lazy, may not be available)
        self._kt   = None   # KnowledgeTank
        self._ng   = None   # NeuroGraph
        self._sb   = None   # SelfBuilder

        self._init()

    # ── init ──────────────────────────────────────────────────────────────────

    def _init(self):
        os.makedirs(self.backend_dir, exist_ok=True)
        os.makedirs(os.path.join(self.backend_dir, "agents"), exist_ok=True)
        self._load_state()
        self._connect_neural_stack()
        logger.info("[Backend] central neural backend ready: %s", self.backend_dir)

    def _connect_neural_stack(self):
        """Lazy-connect to GhostGoat's existing neural systems."""
        try:
            from core.memory.semantic_tank import KnowledgeTank
            self._kt = KnowledgeTank()
        except Exception as e:
            logger.debug("[Backend] KnowledgeTank not available: %s", e)

        try:
            from core.memory.neurograph import NeuroGraph
            self._ng = NeuroGraph()
        except Exception as e:
            logger.debug("[Backend] NeuroGraph not available: %s", e)

        try:
            from core.kernel.build_loop import SelfBuilder
            self._sb = SelfBuilder()
        except Exception as e:
            logger.debug("[Backend] SelfBuilder not available: %s", e)

    # ── state persistence ─────────────────────────────────────────────────────

    def _load_state(self):
        for path, attr in [
            (self._registry_path, "file_registry"),
            (self._agents_path,   "agent_registry"),
        ]:
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        setattr(self, attr, json.load(f))
                except Exception:
                    pass

    def _save_state(self):
        with open(self._registry_path, "w") as f:
            json.dump(self.file_registry, f, indent=2)
        with open(self._agents_path, "w") as f:
            json.dump(self.agent_registry, f, indent=2)

    # ── agent registry ────────────────────────────────────────────────────────

    def register_agent(self, folder_path: str, agent_path: str) -> str:
        agent_id = hashlib.md5(folder_path.encode()).hexdigest()[:8]
        self.agent_registry[agent_id] = {
            "folder":       folder_path,
            "agent_file":   agent_path,
            "created":      self.agent_registry.get(agent_id, {}).get(
                                "created", datetime.now().isoformat()),
            "last_updated": datetime.now().isoformat(),
        }
        self._save_state()

        # Register node in NeuroGraph so agents can query relationships
        if self._ng:
            try:
                rel_folder = os.path.relpath(folder_path, self.root_dir)
                self._ng.add_node(
                    f"agent:{agent_id}",
                    kind="agent",
                    folder=rel_folder,
                    agent_file=agent_path,
                )
            except Exception:
                pass

        return agent_id

    # ── file indexing ──────────────────────────────────────────────────────────

    def index_file(self, filepath: str) -> Optional[dict]:
        """
        Index a file into:
          1. Local file_registry (fast hash-based change detection)
          2. KnowledgeTank (FTS search across all agents)
          3. SelfBuilder (so the system learns from codebase structure)
          4. NeuroGraph (file → folder relationship edges)
        """
        try:
            stat = os.stat(filepath)
        except OSError:
            return None

        file_hash = self._hash_file(filepath)
        existing  = self.file_registry.get(filepath, {})

        # Skip if unchanged — return None so callers know nothing was re-indexed
        if existing.get("hash") == file_hash:
            return None

        metadata = {
            "path":      filepath,
            "size":      stat.st_size,
            "modified":  datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": Path(filepath).suffix,
            "hash":      file_hash,
            "indexed_at": datetime.now().isoformat(),
        }

        self.file_registry[filepath] = metadata

        # ── feed GhostGoat neural systems ─────────────────────────────────────
        self._feed_knowledge_tank(filepath, metadata)
        self._feed_self_builder(filepath)
        self._feed_neurograph(filepath)

        return metadata

    def _feed_knowledge_tank(self, filepath: str, metadata: dict):
        if not self._kt:
            return
        try:
            rel = os.path.relpath(filepath, self.root_dir)
            self._kt.index_algorithm(
                path=filepath,
                name=rel,
                category=_ext_to_category(metadata["extension"]),
                tags=[metadata["extension"], "ordinance_scan"],
            )
        except Exception as e:
            logger.debug("[Backend] KnowledgeTank feed error: %s", e)

    def _feed_self_builder(self, filepath: str):
        if not self._sb:
            return
        try:
            self._sb.ingest_file(filepath)
        except Exception as e:
            logger.debug("[Backend] SelfBuilder feed error: %s", e)

    def _feed_neurograph(self, filepath: str):
        if not self._ng:
            return
        try:
            folder = os.path.dirname(filepath)
            rel    = os.path.relpath(filepath, self.root_dir)
            fid    = f"file:{hashlib.md5(filepath.encode()).hexdigest()[:8]}"
            aid    = f"agent:{hashlib.md5(folder.encode()).hexdigest()[:8]}"
            self._ng.add_node(fid, kind="file", path=rel)
            self._ng.add_edge(aid, fid, relation="contains")
        except Exception as e:
            logger.debug("[Backend] NeuroGraph feed error: %s", e)

    # ── context queries ───────────────────────────────────────────────────────

    def get_folder_context(self, folder_path: str) -> Dict[str, dict]:
        """All indexed files under folder_path (relative paths → metadata)."""
        result = {}
        for filepath, meta in self.file_registry.items():
            if filepath.startswith(folder_path):
                rel = os.path.relpath(filepath, folder_path)
                result[rel] = meta
        return result

    def search(self, query: str, limit: int = 10) -> List[dict]:
        """Full-text search across all indexed files via KnowledgeTank."""
        if self._kt:
            try:
                return self._kt.search(query, limit=limit)
            except Exception:
                pass
        # Fallback: substring match on registry keys
        q = query.lower()
        return [
            {"path": p, **m}
            for p, m in self.file_registry.items()
            if q in p.lower()
        ][:limit]

    def stats(self) -> dict:
        exts: Dict[str, int] = defaultdict(int)
        for m in self.file_registry.values():
            exts[m.get("extension", "")] += 1
        return {
            "files_indexed": len(self.file_registry),
            "agents":        len(self.agent_registry),
            "extensions":    dict(exts),
            "backend_dir":   self.backend_dir,
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_file(filepath: str) -> Optional[str]:
        h = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return None


def _ext_to_category(ext: str) -> str:
    mapping = {
        ".py":   "python",
        ".js":   "javascript",
        ".ts":   "typescript",
        ".json": "config",
        ".yaml": "config",
        ".yml":  "config",
        ".toml": "config",
        ".md":   "documentation",
        ".txt":  "text",
        ".html": "web",
        ".css":  "web",
        ".sql":  "database",
        ".sh":   "shell",
    }
    return mapping.get(ext.lower(), "other")
