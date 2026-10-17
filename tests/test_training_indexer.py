"""Indexing an external repo into the KnowledgeTank: incremental, prunable,
retrievable — the ~/training knowledge path."""

import json
import os
from pathlib import Path

from brain.knowledge.knowledge_tank import KnowledgeTank
from brain.knowledge.repo_indexer import index_repo

OUTPUT_MARKER = "BLOWUP_OUTPUT_MARKER"


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "training"
    (root / "Algorithms").mkdir(parents=True)
    (root / "Algorithms" / "dijkstra.py").write_text(
        'def dijkstra(graph, start):\n    """Single-source shortest paths."""\n    return {}\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Training repo\nNotebooks for machine learning practice.\n", encoding="utf-8"
    )
    nb = {
        "cells": [
            {"cell_type": "markdown",
             "source": ["# Attention\n", "Transformer self-attention explained."]},
            {"cell_type": "code",
             "source": ["x = attention(q, k, v)"],
             "outputs": [{"output_type": "stream", "text": [OUTPUT_MARKER]}],
            },
        ],
        "metadata": {}, "nbformat": 4, "nbformat_minor": 5,
    }
    (root / "attention.ipynb").write_text(json.dumps(nb), encoding="utf-8")
    (root / "binary.py").write_bytes(b"\x00\x01\x02not text")
    (root / ".hidden").mkdir()
    (root / ".hidden" / "secret.md").write_text("hidden marker", encoding="utf-8")
    return root


def make_tank(tmp_path: Path) -> KnowledgeTank:
    return KnowledgeTank(storage_path=str(tmp_path / "tank"))


def test_indexes_repo_and_retrieves(tmp_path):
    tank = make_tank(tmp_path)
    stats = index_repo(tank, make_repo(tmp_path))
    assert stats["indexed"] == 3      # dijkstra.py, README.md, attention.ipynb
    assert stats["scanned"] == 4      # + binary.py (passes filters, fails content)
    assert stats["skipped"] == 1      # binary file
    # natural-language query retrieves the source file
    hits = tank.search("dijkstra shortest path algorithm")
    assert any("dijkstra.py" in h["source"] for h in hits)
    # notebook content is retrievable, outputs never ingested
    hits = tank.search("transformer attention")
    assert any(h["source"].endswith("attention.ipynb") for h in hits)
    all_content = " ".join(e.content for e in tank.entries.values())
    assert OUTPUT_MARKER not in all_content
    # hidden dirs are not indexed
    assert not any("secret" in e.content for e in tank.entries.values())


def test_second_run_is_incremental_and_survives_restart(tmp_path):
    tank = make_tank(tmp_path)
    root = make_repo(tmp_path)
    index_repo(tank, root)
    before = len(tank.entries)

    stats = index_repo(tank, root)
    assert stats["indexed"] == 0
    assert stats["unchanged"] == 3
    assert len(tank.entries) == before

    # a fresh process (new tank instance, same storage) also skips everything
    reloaded = KnowledgeTank(storage_path=str(tmp_path / "tank"))
    stats = index_repo(reloaded, root)
    assert stats["unchanged"] == 3
    assert len(reloaded.entries) == before


def test_changed_file_is_replaced_not_duplicated(tmp_path):
    tank = make_tank(tmp_path)
    root = make_repo(tmp_path)
    index_repo(tank, root)

    changed = root / "Algorithms" / "dijkstra.py"
    changed.write_text("def bellman_ford(graph, start):\n    return {}\n", encoding="utf-8")
    os.utime(changed, (changed.stat().st_atime, changed.stat().st_mtime + 100))

    stats = index_repo(tank, root)
    assert stats["indexed"] == 1
    entries = [e for e in tank.entries.values() if e.source.endswith("dijkstra.py")]
    assert len(entries) == 1
    assert "bellman_ford" in entries[0].content
    assert not any("Single-source shortest paths" in e.content for e in tank.entries.values())


def test_deleted_file_entries_are_pruned(tmp_path):
    tank = make_tank(tmp_path)
    root = make_repo(tmp_path)
    index_repo(tank, root)

    (root / "README.md").unlink()
    stats = index_repo(tank, root)
    assert stats["removed"] == 1
    assert not any(e.source.endswith("README.md") for e in tank.entries.values())


def test_search_retrieves_by_token_overlap(tmp_path):
    tank = make_tank(tmp_path)
    tank.ingest(
        "The Bellman-Ford algorithm computes single-source shortest paths.",
        category="algorithm", tags=["shortest-path"],
    )
    # the full phrase never appears in the content — tokens must still match
    hits = tank.search("bellman ford shortest path")
    assert hits
    assert "Bellman-Ford" in hits[0]["content"]
