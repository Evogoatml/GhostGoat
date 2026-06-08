"""
Tests for core/build_loop.py — BuildLoop autonomous self-assembly engine.
"""

import importlib
import json
import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_sandbox():
    sb = MagicMock()
    result = MagicMock()
    result.passed = True
    result.stdout = "ok"
    result.stderr = ""
    result.error = None
    sb.run.return_value = result
    return sb


@pytest.fixture
def build_loop(tmp_path, mock_sandbox):
    """Create a BuildLoop with a temp dir and mocked sandbox."""
    from core.kernel.build_loop import BuildLoop
    with patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "core" / "wiring"), \
         patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "data" / "build_loop_log.json"), \
         patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "SYSTEM_MAP.md"), \
         patch.object(BuildLoop, 'ROOT', tmp_path):
        loop = BuildLoop(llm_call=lambda prompt: "# generated code\nprint('hello')")
        loop.sandbox = mock_sandbox
        yield loop


@pytest.fixture
def system_map_content():
    return """# SYSTEM MAP

## What's Wired (Connected)
| Component | Status |
|-----------|--------|
| LLMOrchestrator | ✅ |

## What Exists but Isn't Fully Connected Yet
| Component | Gap |
|-----------|-----|
| adap_pipeline tool system | Not bridged yet |
| sandbox execution layer | Needs integration |
| crewai framework | Missing adapter |
"""


# ---------------------------------------------------------------------------
# Gap dataclass
# ---------------------------------------------------------------------------

class TestGap:
    def test_gap_defaults(self):
        from core.kernel.build_loop import Gap
        g = Gap(component="test", description="a gap")
        assert g.priority == 5
        assert g.attempts == 0
        assert g.resolved is False
        assert g.output_file is None

    def test_gap_custom_priority(self):
        from core.kernel.build_loop import Gap
        g = Gap(component="x", description="y", priority=1)
        assert g.priority == 1


# ---------------------------------------------------------------------------
# BuildRecord dataclass
# ---------------------------------------------------------------------------

class TestBuildRecord:
    def test_build_record_has_timestamp(self):
        from core.kernel.build_loop import BuildRecord
        r = BuildRecord(
            gap="test gap",
            attempt=1,
            passed=True,
            file_written="/some/file.py",
            sandbox_stdout="ok",
            sandbox_stderr="",
        )
        assert r.timestamp is not None
        assert isinstance(r.timestamp, str)


# ---------------------------------------------------------------------------
# BuildLoop.__init__
# ---------------------------------------------------------------------------

class TestBuildLoopInit:
    def test_creates_wiring_dir(self, tmp_path):
        wiring_dir = tmp_path / "core" / "wiring"
        assert not wiring_dir.exists()
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'WIRING_DIR', wiring_dir), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "data" / "log.json"), \
             patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "SYSTEM_MAP.md"), \
             patch.object(BuildLoop, 'ROOT', tmp_path):
            BuildLoop(llm_call=lambda p: "")
        assert wiring_dir.exists()

    def test_records_initially_empty(self, build_loop):
        assert build_loop.records == []


# ---------------------------------------------------------------------------
# load_gaps
# ---------------------------------------------------------------------------

class TestLoadGaps:
    def test_empty_when_no_system_map(self, tmp_path):
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "missing.md"), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path):
            loop = BuildLoop(llm_call=lambda p: "")
            gaps = loop.load_gaps()
        assert gaps == []

    def test_parses_gaps_from_system_map(self, tmp_path, system_map_content):
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text(system_map_content)
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path):
            loop = BuildLoop(llm_call=lambda p: "")
            gaps = loop.load_gaps()
        assert len(gaps) >= 1
        components = [g.component for g in gaps]
        assert any("adap_pipeline" in c or "sandbox" in c or "crewai" in c for c in components)

    def test_resolved_gaps_excluded(self, tmp_path):
        content = """## What Exists but Isn't Fully Connected Yet
| Component | Gap |
|-----------|-----|
| ✅ already done | Already fixed |
| open gap | Not done |
"""
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text(content)
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path):
            loop = BuildLoop(llm_call=lambda p: "")
            gaps = loop.load_gaps()
        components = [g.component for g in gaps]
        assert not any("already done" in c for c in components)

    def test_gaps_sorted_by_priority(self, tmp_path, system_map_content):
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text(system_map_content)
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path):
            loop = BuildLoop(llm_call=lambda p: "")
            gaps = loop.load_gaps()
        priorities = [g.priority for g in gaps]
        assert priorities == sorted(priorities)


# ---------------------------------------------------------------------------
# _priority_for
# ---------------------------------------------------------------------------

class TestPriorityFor:
    def test_known_keywords(self, build_loop):
        assert build_loop._priority_for("sandbox execution") == 1
        assert build_loop._priority_for("adap pipeline") == 2
        assert build_loop._priority_for("crewai framework") == 5
        assert build_loop._priority_for("ssh tunnel") == 6

    def test_unknown_defaults_to_5(self, build_loop):
        assert build_loop._priority_for("some unknown component xyz") == 5


# ---------------------------------------------------------------------------
# _write_wiring
# ---------------------------------------------------------------------------

class TestWriteWiring:
    def test_writes_file_with_header(self, tmp_path, mock_sandbox):
        from core.kernel.build_loop import BuildLoop, Gap
        wiring_dir = tmp_path / "core" / "wiring"
        wiring_dir.mkdir(parents=True, exist_ok=True)
        with patch.object(BuildLoop, 'WIRING_DIR', wiring_dir), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "sm.md"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: "")
            gap = Gap(component="test component", description="a gap")
            path = loop._write_wiring(gap, "print('hello')")
        assert Path(path).exists()
        content = Path(path).read_text()
        assert "Auto-generated wiring" in content
        assert "test component" in content
        assert "print('hello')" in content

    def test_slug_sanitized(self, tmp_path, mock_sandbox):
        from core.kernel.build_loop import BuildLoop, Gap
        wiring_dir = tmp_path / "core" / "wiring"
        wiring_dir.mkdir(parents=True, exist_ok=True)
        with patch.object(BuildLoop, 'WIRING_DIR', wiring_dir), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "sm.md"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: "")
            gap = Gap(component="Some Gap! With Spaces & Chars", description="x")
            path = loop._write_wiring(gap, "pass")
        filename = Path(path).name
        assert re.match(r"[a-z0-9_]+\.py", filename)


# ---------------------------------------------------------------------------
# _mark_resolved
# ---------------------------------------------------------------------------

class TestMarkResolved:
    def test_adds_checkmark_to_system_map(self, tmp_path, system_map_content):
        from core.kernel.build_loop import BuildLoop, Gap
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text(system_map_content)
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path):
            loop = BuildLoop(llm_call=lambda p: "")
            gap = Gap(component="adap_pipeline tool system", description="x")
            loop._mark_resolved(gap)
        updated = sm.read_text()
        assert "✅ adap_pipeline tool system" in updated


# ---------------------------------------------------------------------------
# _save_log
# ---------------------------------------------------------------------------

class TestSaveLog:
    def test_saves_json_log(self, tmp_path, mock_sandbox):
        from core.kernel.build_loop import BuildLoop, BuildRecord
        log_path = tmp_path / "data" / "log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with patch.object(BuildLoop, 'BUILD_LOG', log_path), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "sm.md"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: "")
            loop.records = [
                BuildRecord(
                    gap="test gap",
                    attempt=1,
                    passed=True,
                    file_written="/some/file.py",
                    sandbox_stdout="ok",
                    sandbox_stderr="",
                )
            ]
            loop._save_log()
        data = json.loads(log_path.read_text())
        assert len(data) == 1
        assert data[0]["gap"] == "test gap"
        assert data[0]["passed"] is True

    def test_appends_to_existing_log(self, tmp_path, mock_sandbox):
        from core.kernel.build_loop import BuildLoop, BuildRecord
        log_path = tmp_path / "data" / "log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps([{"gap": "old", "passed": False}]))
        with patch.object(BuildLoop, 'BUILD_LOG', log_path), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "sm.md"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: "")
            loop.records = [
                BuildRecord("new gap", 1, True, None, "", "")
            ]
            loop._save_log()
        data = json.loads(log_path.read_text())
        assert len(data) == 2
        assert data[0]["gap"] == "old"
        assert data[1]["gap"] == "new gap"


# ---------------------------------------------------------------------------
# _generate_wiring
# ---------------------------------------------------------------------------

class TestGenerateWiring:
    def test_returns_none_without_llm(self, tmp_path, mock_sandbox):
        from core.kernel.build_loop import BuildLoop, Gap
        with patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'SYSTEM_MAP', tmp_path / "sm.md"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=None)
            gap = Gap(component="test", description="x")
            result = loop._generate_wiring(gap, 1)
        assert result is None

    def test_strips_markdown_fences(self, tmp_path, mock_sandbox):
        llm_response = "```python\nprint('hello')\n```"
        from core.kernel.build_loop import BuildLoop, Gap
        sm_path = tmp_path / "SYSTEM_MAP.md"
        sm_path.write_text("## What's Wired Yet\n")
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm_path), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: llm_response)
            gap = Gap(component="test", description="x")
            result = loop._generate_wiring(gap, 1)
        assert "```" not in result
        assert "print('hello')" in result

    def test_calls_llm_with_gap_info(self, tmp_path, mock_sandbox):
        prompts = []
        from core.kernel.build_loop import BuildLoop, Gap
        sm_path = tmp_path / "SYSTEM_MAP.md"
        sm_path.write_text("## What's Wired Yet\n")
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm_path), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            def capture_llm(prompt):
                prompts.append(prompt)
                return "pass"
            loop = BuildLoop(llm_call=capture_llm)
            gap = Gap(component="special_component", description="needs bridge")
            loop._generate_wiring(gap, 1)
        assert len(prompts) == 1
        assert "special_component" in prompts[0]
        assert "needs bridge" in prompts[0]


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

class TestRun:
    def test_run_no_gaps(self, tmp_path, mock_sandbox):
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text("# No gaps section here\n")
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: "")
            loop.run()
        assert loop.records == []

    def test_run_with_gap_filter(self, tmp_path, system_map_content, mock_sandbox):
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text(system_map_content)
        wiring_dir = tmp_path / "core" / "wiring"
        wiring_dir.mkdir(parents=True, exist_ok=True)
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', wiring_dir), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: "")
            loop._ingest = lambda f: None
            loop.run(gap_filter="nonexistent_filter_xyz")
        assert loop.records == []

    def test_run_max_cycles(self, tmp_path, system_map_content, mock_sandbox):
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text(system_map_content)
        wiring_dir = tmp_path / "core" / "wiring"
        wiring_dir.mkdir(parents=True, exist_ok=True)
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', wiring_dir), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path), \
             patch("core.kernel.build_loop.Sandbox", return_value=mock_sandbox):
            loop = BuildLoop(llm_call=lambda p: "")
            loop._ingest = lambda f: None
            loop._mark_resolved = lambda g: None
            loop.run(max_cycles=1)
        attempted = len(loop.records)
        assert attempted <= 3


# ---------------------------------------------------------------------------
# status()
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_prints(self, tmp_path, capsys, system_map_content):
        sm = tmp_path / "SYSTEM_MAP.md"
        sm.write_text(system_map_content)
        from core.kernel.build_loop import BuildLoop
        with patch.object(BuildLoop, 'SYSTEM_MAP', sm), \
             patch.object(BuildLoop, 'WIRING_DIR', tmp_path / "w"), \
             patch.object(BuildLoop, 'BUILD_LOG', tmp_path / "l.json"), \
             patch.object(BuildLoop, 'ROOT', tmp_path):
            loop = BuildLoop(llm_call=lambda p: "")
            loop.status()
        captured = capsys.readouterr()
        assert "GhostGoat Build Status" in captured.out
        assert "Open gaps" in captured.out
