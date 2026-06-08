"""
Tests for core/ordinance/
Covers: CentralNeuralBackend, FolderAgent, DistributedAgentSystem, OrdinanceClient

All tests are fully isolated via tmp_path — no real .backend/ or AGENT.md
files are written to the repo.  GhostGoat neural systems (KnowledgeTank,
NeuroGraph, SelfBuilder) are stubbed out so tests pass without heavy deps.
"""
import json
import os
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_file(path: str, content: str = "hello") -> str:
    """Create a file with content and return its path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path


@pytest.fixture()
def root(tmp_path):
    """A clean root directory with a small tree of Python + JSON files."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "agents").mkdir()
    _make_file(str(tmp_path / "core" / "main.py"),        "print('main')")
    _make_file(str(tmp_path / "core" / "config.json"),    '{"key": "val"}')
    _make_file(str(tmp_path / "core" / "agents" / "a.py"), "class A: pass")
    _make_file(str(tmp_path / "core" / "agents" / "b.py"), "class B: pass")
    _make_file(str(tmp_path / "README.md"),                "# Project")
    return tmp_path


@pytest.fixture()
def backend(root, monkeypatch):
    """CentralNeuralBackend with neural stack stubbed out (no heavy deps)."""
    from core.ordinance.central_backend import CentralNeuralBackend

    # Stub out neural integrations so tests don't need KnowledgeTank etc.
    monkeypatch.setattr(
        CentralNeuralBackend, "_connect_neural_stack", lambda self: None
    )
    return CentralNeuralBackend(root_dir=str(root))


# ══════════════════════════════════════════════════════════════════════════════
# CentralNeuralBackend
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCentralNeuralBackend:

    def test_backend_dir_created(self, backend, root):
        assert os.path.isdir(os.path.join(str(root), ".backend"))

    def test_index_file_returns_metadata(self, backend, root):
        fp = str(root / "core" / "main.py")
        meta = backend.index_file(fp)
        assert meta is not None
        assert meta["path"] == fp
        assert meta["extension"] == ".py"
        assert isinstance(meta["size"], int)
        assert "hash" in meta

    def test_index_file_skips_unchanged(self, backend, root):
        fp = str(root / "core" / "main.py")
        backend.index_file(fp)
        first_ts = backend.file_registry[fp]["indexed_at"]

        # Second call with same content — hash match → return None (skipped)
        meta2 = backend.index_file(fp)
        assert meta2 is None
        # Registry entry untouched
        assert backend.file_registry[fp]["indexed_at"] == first_ts

    def test_index_file_reindexes_when_changed(self, backend, root):
        fp = str(root / "core" / "main.py")
        backend.index_file(fp)

        # Change the file
        with open(fp, "a") as f:
            f.write("\n# changed")

        meta2 = backend.index_file(fp)
        assert meta2 is not None
        # Hash will differ → new metadata
        assert meta2["indexed_at"] != backend.file_registry[fp].get("_first_ts", "")

    def test_index_missing_file_returns_none(self, backend):
        result = backend.index_file("/does/not/exist.py")
        assert result is None

    def test_registry_persists_to_disk(self, backend, root):
        fp = str(root / "core" / "config.json")
        backend.index_file(fp)
        backend._save_state()

        # Re-load from disk
        from core.ordinance.central_backend import CentralNeuralBackend
        import unittest.mock as mock
        with mock.patch.object(CentralNeuralBackend, "_connect_neural_stack",
                               lambda self: None):
            backend2 = CentralNeuralBackend(root_dir=str(root))

        assert fp in backend2.file_registry

    def test_get_folder_context_returns_subfolder_files(self, backend, root):
        for f in ["core/main.py", "core/config.json",
                  "core/agents/a.py", "core/agents/b.py"]:
            backend.index_file(str(root / f))

        ctx = backend.get_folder_context(str(root / "core"))
        assert len(ctx) == 4

    def test_get_folder_context_relative_keys(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        ctx = backend.get_folder_context(str(root / "core"))
        assert "main.py" in ctx

    def test_get_folder_context_excludes_other_folders(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        backend.index_file(str(root / "README.md"))

        ctx = backend.get_folder_context(str(root / "core"))
        for key in ctx:
            assert "README" not in key

    def test_get_folder_context_empty_when_no_files(self, backend, root):
        ctx = backend.get_folder_context(str(root / "core"))
        assert ctx == {}

    def test_register_agent_returns_8char_id(self, backend, root):
        aid = backend.register_agent(str(root / "core"), str(root / "core" / "AGENT.md"))
        assert isinstance(aid, str)
        assert len(aid) == 8

    def test_register_agent_is_deterministic(self, backend, root):
        folder = str(root / "core")
        id1 = backend.register_agent(folder, "AGENT.md")
        id2 = backend.register_agent(folder, "AGENT.md")
        assert id1 == id2

    def test_register_agent_different_folders_differ(self, backend, root):
        id1 = backend.register_agent(str(root / "core"),          "a.md")
        id2 = backend.register_agent(str(root / "core" / "agents"), "b.md")
        assert id1 != id2

    def test_agent_registry_persists(self, backend, root):
        backend.register_agent(str(root / "core"), str(root / "core" / "AGENT.md"))
        backend._save_state()
        assert os.path.exists(backend._agents_path)
        with open(backend._agents_path) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_search_fallback_substring(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        backend.index_file(str(root / "core" / "config.json"))
        results = backend.search("main")
        paths = [r["path"] for r in results]
        assert any("main.py" in p for p in paths)
        assert all("config" not in p for p in paths)

    def test_search_returns_at_most_limit(self, backend, root):
        for f in ["core/main.py", "core/config.json",
                  "core/agents/a.py", "core/agents/b.py"]:
            backend.index_file(str(root / f))
        results = backend.search("core", limit=2)
        assert len(results) <= 2

    def test_stats_structure(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        s = backend.stats()
        assert "files_indexed" in s
        assert "agents" in s
        assert "extensions" in s
        assert s["files_indexed"] == 1

    def test_stats_extension_grouping(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        backend.index_file(str(root / "core" / "config.json"))
        s = backend.stats()
        assert ".py"   in s["extensions"]
        assert ".json" in s["extensions"]

    def test_hash_file_consistent(self, backend, root):
        fp = str(root / "core" / "main.py")
        h1 = backend._hash_file(fp)
        h2 = backend._hash_file(fp)
        assert h1 == h2
        assert h1 is not None

    def test_hash_file_missing_returns_none(self, backend):
        assert backend._hash_file("/no/such/file.py") is None


# ══════════════════════════════════════════════════════════════════════════════
# FolderAgent
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestFolderAgent:

    def test_generate_creates_agent_md(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        from core.ordinance.folder_agent import FolderAgent
        agent = FolderAgent(str(root / "core"), backend)
        agent.generate()
        assert os.path.exists(str(root / "core" / "AGENT.md"))

    def test_agent_md_contains_folder_name(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        from core.ordinance.folder_agent import FolderAgent
        agent = FolderAgent(str(root / "core"), backend)
        agent.generate()
        content = open(str(root / "core" / "AGENT.md")).read()
        assert "core" in content

    def test_agent_md_lists_files(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        from core.ordinance.folder_agent import FolderAgent
        agent = FolderAgent(str(root / "core"), backend)
        agent.generate()
        content = open(str(root / "core" / "AGENT.md")).read()
        assert "main.py" in content

    def test_agent_md_contains_agent_id(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        from core.ordinance.folder_agent import FolderAgent
        agent = FolderAgent(str(root / "core"), backend)
        agent.generate()
        assert agent.agent_id is not None
        content = open(str(root / "core" / "AGENT.md")).read()
        assert agent.agent_id in content

    def test_agent_md_contains_ordinance_client_snippet(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        from core.ordinance.folder_agent import FolderAgent
        agent = FolderAgent(str(root / "core"), backend)
        agent.generate()
        content = open(str(root / "core" / "AGENT.md")).read()
        assert "OrdinanceClient" in content

    def test_update_overwrites_existing(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        from core.ordinance.folder_agent import FolderAgent
        agent = FolderAgent(str(root / "core"), backend)
        agent.generate()
        first = open(str(root / "core" / "AGENT.md")).read()

        # Add a file and regenerate
        _make_file(str(root / "core" / "extra.py"), "x = 1")
        backend.index_file(str(root / "core" / "extra.py"))
        agent.update()
        second = open(str(root / "core" / "AGENT.md")).read()

        assert "extra.py" in second
        assert second != first    # file was updated

    def test_agent_md_groups_by_extension(self, backend, root):
        backend.index_file(str(root / "core" / "main.py"))
        backend.index_file(str(root / "core" / "config.json"))
        from core.ordinance.folder_agent import FolderAgent
        agent = FolderAgent(str(root / "core"), backend)
        agent.generate()
        content = open(str(root / "core" / "AGENT.md")).read()
        assert ".py"   in content
        assert ".json" in content

    def test_empty_folder_generates_minimal_agent_md(self, backend, root):
        """Folder with no indexed files still gets an AGENT.md (0 files)."""
        from core.ordinance.folder_agent import FolderAgent
        empty_dir = str(root / "empty_dir")
        os.makedirs(empty_dir, exist_ok=True)
        agent = FolderAgent(empty_dir, backend)
        agent.generate()
        content = open(str(empty_dir + "/AGENT.md")).read()
        assert "0" in content   # 0 files


# ══════════════════════════════════════════════════════════════════════════════
# DistributedAgentSystem
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestDistributedAgentSystem:

    @pytest.fixture()
    def system(self, root, monkeypatch):
        from core.ordinance.central_backend import CentralNeuralBackend
        from core.ordinance.distributed_system import DistributedAgentSystem
        monkeypatch.setattr(
            CentralNeuralBackend, "_connect_neural_stack", lambda self: None
        )
        return DistributedAgentSystem(root_dir=str(root))

    def test_scan_returns_stats_dict(self, system):
        stats = system.scan()
        assert isinstance(stats, dict)
        for key in ("root", "files_indexed", "files_skipped", "agents", "backend"):
            assert key in stats

    def test_scan_indexes_py_files(self, system, root):
        stats = system.scan()
        assert stats["files_indexed"] >= 3   # main.py, a.py, b.py

    def test_scan_creates_agent_md_in_each_folder(self, system, root):
        system.scan()
        assert os.path.exists(str(root / "core" / "AGENT.md"))
        assert os.path.exists(str(root / "core" / "agents" / "AGENT.md"))

    def test_scan_skips_excluded_dir(self, system, root):
        # Put a file inside a directory that should be excluded
        excluded = root / "__pycache__"
        excluded.mkdir()
        _make_file(str(excluded / "cache.py"), "x = 1")

        system.scan()
        # The excluded folder must NOT get an AGENT.md
        assert not os.path.exists(str(excluded / "AGENT.md"))

    def test_scan_skips_non_matching_extension(self, system, root, tmp_path):
        # .so binary — not in default extensions
        _make_file(str(root / "core" / "lib.so"), "\x7fELF")
        stats = system.scan()
        # lib.so should not appear in any AGENT.md
        content = open(str(root / "core" / "AGENT.md")).read()
        assert "lib.so" not in content

    def test_scan_does_not_index_agent_md_itself(self, system, root):
        # First scan generates AGENT.md; second scan should not index it
        system.scan()
        stats2 = system.scan()
        content = open(str(root / "core" / "AGENT.md")).read()
        # AGENT.md should not list itself as a tracked file
        lines = [l for l in content.splitlines() if "AGENT.md" in l and "`AGENT.md`" in l]
        # Only the header "Auto-generated…" line should mention it, not the file list
        assert len(lines) == 0

    def test_list_agents_returns_all(self, system):
        system.scan()
        agents = system.list_agents()
        assert len(agents) >= 2   # core/ and core/agents/

    def test_list_agents_structure(self, system):
        system.scan()
        for a in system.list_agents():
            assert "agent_id" in a
            assert "folder"   in a
            assert "updated"  in a

    def test_update_all_refreshes_content(self, system, root):
        system.scan()
        # Add a new file
        _make_file(str(root / "core" / "new_module.py"), "y = 2")
        system.backend.index_file(str(root / "core" / "new_module.py"))
        system.update_all()
        content = open(str(root / "core" / "AGENT.md")).read()
        assert "new_module.py" in content

    def test_scan_idempotent(self, system):
        stats1 = system.scan()
        stats2 = system.scan()
        # Second scan: all files already hashed → 0 newly indexed
        assert stats2["files_indexed"] == 0
        assert stats2["agents"] == stats1["agents"]


# ══════════════════════════════════════════════════════════════════════════════
# OrdinanceClient
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestOrdinanceClient:

    @pytest.fixture()
    def populated_client(self, root, monkeypatch):
        """Client backed by a root that has already been scanned."""
        from core.ordinance.central_backend import CentralNeuralBackend
        from core.ordinance.distributed_system import DistributedAgentSystem
        from core.ordinance.ordinance_client import OrdinanceClient

        monkeypatch.setattr(
            CentralNeuralBackend, "_connect_neural_stack", lambda self: None
        )
        system = DistributedAgentSystem(root_dir=str(root))
        system.scan()

        monkeypatch.setattr(
            CentralNeuralBackend, "_connect_neural_stack", lambda self: None
        )
        return OrdinanceClient(root_dir=str(root))

    def test_get_folder_context_absolute_path(self, populated_client, root):
        ctx = populated_client.get_folder_context(str(root / "core"))
        assert any("main.py" in k for k in ctx)

    def test_get_folder_context_relative_path(self, populated_client, root):
        ctx = populated_client.get_folder_context("core")
        assert len(ctx) > 0

    def test_get_folder_context_returns_metadata(self, populated_client, root):
        ctx = populated_client.get_folder_context(str(root / "core"))
        meta = next(iter(ctx.values()))
        assert "size" in meta
        assert "modified" in meta
        assert "hash" in meta

    def test_search_finds_by_filename(self, populated_client):
        results = populated_client.search("main")
        assert any("main" in r.get("path", "") for r in results)

    def test_search_returns_empty_for_no_match(self, populated_client):
        results = populated_client.search("zzz_no_such_file_xyz")
        assert results == []

    def test_search_respects_limit(self, populated_client):
        results = populated_client.search("core", limit=1)
        assert len(results) <= 1

    def test_list_agents_not_empty(self, populated_client):
        agents = populated_client.list_agents()
        assert len(agents) >= 2

    def test_list_agents_have_required_fields(self, populated_client):
        for a in populated_client.list_agents():
            assert "agent_id" in a
            assert "folder"   in a
            assert "updated"  in a

    def test_stats_counts_are_positive(self, populated_client):
        s = populated_client.stats()
        assert s["files_indexed"] > 0
        assert s["agents"]        > 0

    def test_get_neighbours_returns_list(self, populated_client):
        """get_neighbours with no NeuroGraph returns [] gracefully."""
        agents = populated_client.list_agents()
        first_id = agents[0]["agent_id"]
        result = populated_client.get_neighbours(first_id)
        assert isinstance(result, list)

    def test_get_neighbours_invalid_id_returns_empty(self, populated_client):
        result = populated_client.get_neighbours("deadbeef")
        assert result == []
