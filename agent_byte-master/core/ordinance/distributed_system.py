"""
Distributed Agent System
=========================

Scans the entire GhostGoat repository (or any root dir),
indexes every file into the central neural backend, and
auto-generates AGENT.md in every folder.

Key differences from the original standalone script
----------------------------------------------------
- No duplicate storage: uses KnowledgeTank + NeuroGraph + SelfBuilder
  instead of a separate pickle knowledge graph
- Hash-based change detection: re-scans only changed files
- Watcher mode: optionally monitors for file-system changes
- CLI-usable:  python -m core.ordinance [--root .] [--watch]
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, Set

from core.ordinance.central_backend import CentralNeuralBackend
from core.ordinance.folder_agent import FolderAgent

logger = logging.getLogger(__name__)

# ── defaults ──────────────────────────────────────────────────────────────────

EXCLUDE_DIRS: Set[str] = {
    ".git", ".backend", "__pycache__", "node_modules",
    ".venv", "venv", ".idea", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".eggs",
}

INCLUDE_EXTENSIONS: Set[str] = {
    ".py", ".js", ".ts", ".json", ".txt", ".md",
    ".yaml", ".yml", ".toml", ".csv", ".html", ".css",
    ".sql", ".sh", ".env.example", ".cfg", ".ini",
}


class DistributedAgentSystem:
    """
    Creates one FolderAgent per folder and keeps them in sync
    with the central neural backend.
    """

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = root_dir or os.getcwd()
        self.backend  = CentralNeuralBackend(self.root_dir)
        self._agents:  List[FolderAgent] = []

    # ── public API ─────────────────────────────────────────────────────────────

    def scan(self,
             exclude_dirs:  Optional[Set[str]] = None,
             extensions:    Optional[Set[str]] = None,
             skip_unchanged: bool = True) -> dict:
        """
        Scan root_dir, index all matching files, generate/update AGENT.md files.
        Returns a stats dict.
        """
        excl = exclude_dirs or EXCLUDE_DIRS
        exts = extensions   or INCLUDE_EXTENSIONS

        logger.info("[Ordinance] scanning from: %s", self.root_dir)

        folders_with_files: Set[str] = set()
        files_indexed = 0
        files_skipped = 0

        # ── pass 1: index all files ───────────────────────────────────────────
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in excl]

            for filename in files:
                if filename == "AGENT.md":
                    continue
                filepath = os.path.join(root, filename)
                if exts and Path(filepath).suffix not in exts:
                    continue

                meta = self.backend.index_file(filepath)
                if meta is not None:
                    files_indexed += 1
                else:
                    files_skipped += 1
                # Track folder regardless — it needs an AGENT.md even if cached
                if Path(filepath).suffix in exts:
                    folders_with_files.add(root)

        self.backend._save_state()

        # ── pass 2: generate AGENT.md per folder ─────────────────────────────
        self._agents = []
        for folder in sorted(folders_with_files):
            agent = FolderAgent(folder, self.backend)
            agent.generate()
            self._agents.append(agent)

        stats = {
            "root":          self.root_dir,
            "files_indexed": files_indexed,
            "files_skipped": files_skipped,
            "agents":        len(self._agents),
            "backend":       self.backend.backend_dir,
        }
        logger.info("[Ordinance] scan complete: %s", stats)
        return stats

    def update_all(self):
        """Refresh all existing AGENT.md files."""
        for agent in self._agents:
            agent.update()
        logger.info("[Ordinance] updated %d agents", len(self._agents))

    def list_agents(self) -> List[dict]:
        return [
            {
                "agent_id": aid,
                "folder":   os.path.relpath(info["folder"], self.root_dir),
                "updated":  info.get("last_updated", "")[:19],
            }
            for aid, info in self.backend.agent_registry.items()
        ]

    def watch(self,
              poll_secs: float = 30,
              exclude_dirs: Optional[Set[str]] = None,
              extensions:   Optional[Set[str]] = None):
        """
        Continuously watch for file changes and re-scan.
        Runs in the calling thread (blocking).
        Uses watchdog if installed, falls back to poll.
        """
        try:
            self._watch_watchdog(poll_secs, exclude_dirs, extensions)
        except ImportError:
            self._watch_poll(poll_secs, exclude_dirs, extensions)

    def _watch_watchdog(self, poll_secs, exclude_dirs, extensions):
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        system = self

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if not event.is_directory and not event.src_path.endswith("AGENT.md"):
                    system.scan(exclude_dirs=exclude_dirs,
                                extensions=extensions)

        obs = Observer()
        obs.schedule(Handler(), self.root_dir, recursive=True)
        obs.start()
        logger.info("[Ordinance] watchdog active (poll=%.0fs)", poll_secs)
        try:
            import time
            while True:
                time.sleep(poll_secs)
        finally:
            obs.stop()
            obs.join()

    def _watch_poll(self, poll_secs, exclude_dirs, extensions):
        import time
        logger.info("[Ordinance] polling every %.0fs (install watchdog for fs events)",
                    poll_secs)
        while True:
            self.scan(exclude_dirs=exclude_dirs, extensions=extensions)
            time.sleep(poll_secs)
