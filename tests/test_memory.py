"""
Unit tests for core/memory/unified_memory.py

Uses only InMemoryBackend (no ChromaDB / sentence-transformers required).
"""

import asyncio
import pytest


def _in_memory_config():
    from config.unified_config import MemoryConfig, MemoryBackend
    return MemoryConfig(backend=MemoryBackend.MEMORY)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# MemoryItem
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMemoryItem:

    def test_auto_timestamp(self):
        from core.memory.unified_memory import MemoryItem
        item = MemoryItem(id="1", content="hello", metadata={})
        assert item.timestamp is not None

    def test_explicit_timestamp_preserved(self):
        from core.memory.unified_memory import MemoryItem
        item = MemoryItem(id="2", content="world", metadata={}, timestamp="2024-01-01T00:00:00")
        assert item.timestamp == "2024-01-01T00:00:00"


# ---------------------------------------------------------------------------
# InMemoryBackend
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestInMemoryBackend:

    def test_store_returns_id(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        mem_id = _run(backend.store("hello world"))
        assert isinstance(mem_id, str) and mem_id

    def test_store_and_retrieve_match(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        _run(backend.store("python programming language"))
        results = _run(backend.retrieve("python"))
        assert len(results) == 1
        assert "python" in results[0].content.lower()

    def test_retrieve_no_match_returns_empty(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        _run(backend.store("completely unrelated content"))
        results = _run(backend.retrieve("quantum physics"))
        assert results == []

    def test_retrieve_top_k_limits_results(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        for i in range(5):
            _run(backend.store(f"matching content item {i}"))
        results = _run(backend.retrieve("matching content", top_k=3))
        assert len(results) <= 3

    def test_retrieve_sorted_by_recency(self):
        from core.memory.unified_memory import InMemoryBackend
        import time
        backend = InMemoryBackend(_in_memory_config())
        _run(backend.store("first item about cats"))
        time.sleep(0.01)  # ensure distinct timestamps
        id2 = _run(backend.store("second item about cats"))
        results = _run(backend.retrieve("cats"))
        # Most recent should come first
        assert results[0].id == id2

    def test_delete_existing_item(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        mem_id = _run(backend.store("delete me"))
        deleted = _run(backend.delete(mem_id))
        assert deleted is True
        results = _run(backend.retrieve("delete"))
        assert results == []

    def test_delete_nonexistent_returns_false(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        deleted = _run(backend.delete("nonexistent-id-xyz"))
        assert deleted is False

    def test_get_stats(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        _run(backend.store("item one"))
        _run(backend.store("item two"))
        stats = _run(backend.get_stats())
        assert stats["count"] == 2
        assert stats["backend"] == "in-memory"

    def test_store_with_metadata(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        _run(backend.store("tagged content", metadata={"tag": "important"}))
        results = _run(backend.retrieve("tagged"))
        assert results[0].metadata.get("tag") == "important"

    def test_store_metadata_always_has_timestamp(self):
        from core.memory.unified_memory import InMemoryBackend
        backend = InMemoryBackend(_in_memory_config())
        _run(backend.store("ts check"))
        results = _run(backend.retrieve("ts check"))
        assert "timestamp" in results[0].metadata


# ---------------------------------------------------------------------------
# UnifiedMemory (facade)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUnifiedMemory:

    def test_store_and_retrieve(self):
        from core.memory.unified_memory import UnifiedMemory
        mem = UnifiedMemory(_in_memory_config())
        _run(mem.store("unified facade test"))
        results = _run(mem.retrieve("unified"))
        assert len(results) == 1

    def test_delete(self):
        from core.memory.unified_memory import UnifiedMemory
        mem = UnifiedMemory(_in_memory_config())
        mid = _run(mem.store("to be deleted"))
        assert _run(mem.delete(mid)) is True

    def test_get_stats(self):
        from core.memory.unified_memory import UnifiedMemory
        mem = UnifiedMemory(_in_memory_config())
        _run(mem.store("one"))
        stats = _run(mem.get_stats())
        assert stats["count"] == 1

    def test_switch_backend_changes_backend(self):
        from core.memory.unified_memory import UnifiedMemory, InMemoryBackend
        from config.unified_config import MemoryBackend
        mem = UnifiedMemory(_in_memory_config())
        mem.switch_backend(MemoryBackend.MEMORY)
        assert isinstance(mem.backend, InMemoryBackend)

    def test_unknown_backend_falls_back_to_in_memory(self):
        from core.memory.unified_memory import UnifiedMemory, InMemoryBackend
        from config.unified_config import MemoryConfig, MemoryBackend
        cfg = MemoryConfig(backend=MemoryBackend.MEMORY)
        cfg.backend = "totally_unknown"  # type: ignore[assignment]
        mem = UnifiedMemory(cfg)
        assert isinstance(mem.backend, InMemoryBackend)


# ---------------------------------------------------------------------------
# create_memory factory
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_memory_with_explicit_config():
    from core.memory.unified_memory import create_memory, UnifiedMemory
    mem = create_memory(_in_memory_config())
    assert isinstance(mem, UnifiedMemory)
