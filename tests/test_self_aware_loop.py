"""
Tests for core/self_aware_loop.py — SelfAwareLoop self-healing feedback loop.
"""

import asyncio
import gc
import time
import threading
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_core():
    """Mock CoreIntegration with all subsystem attributes."""
    core = MagicMock()
    core.neurograph = None
    core.diagnostics = None
    core.asi = None
    core.observe_performance = MagicMock()
    return core


@pytest.fixture
def loop(mock_core):
    from core.brain.agents.self_aware_loop import SelfAwareLoop
    return SelfAwareLoop(mock_core)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_initial_state(self, loop):
        assert loop.running is False
        assert loop._thread is None
        assert loop.heals_performed == 0
        assert loop.optimizations_run == 0
        assert loop.cycles_completed == 0
        assert loop.health_history == []

    def test_default_interval(self, loop):
        assert loop.check_interval == 30.0

    def test_min_max_interval(self, loop):
        assert loop._min_interval == 10.0
        assert loop._max_interval == 120.0

    def test_max_history(self, loop):
        assert loop._max_history == 500


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------

class TestStartStop:
    def test_start_sets_running(self, loop):
        with patch("threading.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = False
            mock_thread_cls.return_value = mock_thread
            loop.start()
        assert loop.running is True

    def test_start_launches_thread(self, loop):
        with patch("threading.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = False
            mock_thread_cls.return_value = mock_thread
            loop.start()
            mock_thread.start.assert_called_once()

    def test_start_idempotent(self, loop):
        """Calling start() twice when already running does nothing."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        loop._thread = mock_thread
        loop.running = True
        with patch("core.brain.agents.self_aware_loop.threading.Thread"):
            loop.start()
            # running is already True and thread is alive — start should be a no-op
            assert loop.running is True

    def test_stop_clears_running(self, loop):
        loop.running = True
        loop.stop()
        assert loop.running is False


# ---------------------------------------------------------------------------
# status()
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_returns_dict(self, loop):
        s = loop.status()
        assert isinstance(s, dict)

    def test_status_has_required_keys(self, loop):
        s = loop.status()
        for key in ("running", "cycles_completed", "heals_performed",
                    "optimizations_run", "current_interval_s", "history_size",
                    "recent_anomalies"):
            assert key in s, f"Missing key: {key}"

    def test_status_reflects_counters(self, loop):
        loop.heals_performed = 3
        loop.cycles_completed = 10
        loop.optimizations_run = 2
        s = loop.status()
        assert s["heals_performed"] == 3
        assert s["cycles_completed"] == 10
        assert s["optimizations_run"] == 2

    def test_status_recent_anomalies_empty_history(self, loop):
        assert loop.status()["recent_anomalies"] == []

    def test_status_recent_anomalies_from_history(self, loop):
        loop.health_history = [
            {"timestamp": "t1", "anomaly_count": 1, "anomaly_types": ["gc_pressure"], "cycle": 0}
        ]
        s = loop.status()
        assert s["recent_anomalies"] == ["gc_pressure"]

    def test_status_history_size(self, loop):
        loop.health_history = [{"x": i} for i in range(5)]
        assert loop.status()["history_size"] == 5


# ---------------------------------------------------------------------------
# _detect_anomalies
# ---------------------------------------------------------------------------

class TestDetectAnomalies:
    def test_empty_snapshot_no_anomalies(self, loop):
        snapshot = {
            "timestamp": "now",
            "neurograph": None,
            "diagnostics": None,
            "optimizer": None,
            "monitoring": None,
            "asi": None,
            "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        assert anomalies == []

    def test_neurograph_unhealthy(self, loop):
        snapshot = {
            "neurograph": {"ok": False, "reason": "broken"},
            "diagnostics": None, "asi": None, "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        types = [a["type"] for a in anomalies]
        assert "graph_unhealthy" in types

    def test_neurograph_many_isolates(self, loop):
        snapshot = {
            "neurograph": {"ok": True, "isolates": list(range(15))},
            "diagnostics": None, "asi": None, "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        types = [a["type"] for a in anomalies]
        assert "many_isolates" in types

    def test_neurograph_few_isolates_no_anomaly(self, loop):
        snapshot = {
            "neurograph": {"ok": True, "isolates": [1, 2]},
            "diagnostics": None, "asi": None, "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        types = [a["type"] for a in anomalies]
        assert "many_isolates" not in types

    def test_missing_files_anomaly(self, loop):
        snapshot = {
            "neurograph": None,
            "diagnostics": {"missing_required_files": ["core/foo.py"]},
            "asi": None, "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        types = [a["type"] for a in anomalies]
        assert "missing_files" in types

    def test_memory_critical(self, loop):
        snapshot = {
            "neurograph": None, "diagnostics": None,
            "asi": {"memory": {"virtual": {"percent": 90}}},
            "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        types = [a["type"] for a in anomalies]
        assert "memory_critical" in types

    def test_memory_warning(self, loop):
        snapshot = {
            "neurograph": None, "diagnostics": None,
            "asi": {"memory": {"virtual": {"percent": 75}}},
            "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        types = [a["type"] for a in anomalies]
        assert "memory_warning" in types

    def test_memory_ok_no_anomaly(self, loop):
        snapshot = {
            "neurograph": None, "diagnostics": None,
            "asi": {"memory": {"virtual": {"percent": 50}}},
            "memory_py": {},
        }
        anomalies = loop._detect_anomalies(snapshot)
        assert anomalies == []

    def test_gc_pressure_anomaly(self, loop):
        snapshot = {
            "neurograph": None, "diagnostics": None, "asi": None,
            "memory_py": {"gc_counts": (800, 5, 0)},
        }
        anomalies = loop._detect_anomalies(snapshot)
        types = [a["type"] for a in anomalies]
        assert "gc_pressure" in types

    def test_gc_no_pressure(self, loop):
        snapshot = {
            "neurograph": None, "diagnostics": None, "asi": None,
            "memory_py": {"gc_counts": (100, 5, 0)},
        }
        anomalies = loop._detect_anomalies(snapshot)
        assert anomalies == []


# ---------------------------------------------------------------------------
# _adapt_interval
# ---------------------------------------------------------------------------

class TestAdaptInterval:
    def test_interval_decreases_on_anomaly(self, loop):
        loop.check_interval = 60.0
        anomalies = [{"type": "gc_pressure", "severity": "low"}]
        loop._adapt_interval({}, anomalies)
        assert loop.check_interval < 60.0

    def test_interval_goes_to_min_on_critical(self, loop):
        loop.check_interval = 60.0
        anomalies = [{"type": "memory_critical", "severity": "critical"}]
        loop._adapt_interval({}, anomalies)
        assert loop.check_interval == loop._min_interval

    def test_interval_increases_when_stable(self, loop):
        loop.check_interval = 30.0
        loop._adapt_interval({}, [])
        assert loop.check_interval > 30.0

    def test_interval_caps_at_max(self, loop):
        loop.check_interval = loop._max_interval
        loop._adapt_interval({}, [])
        assert loop.check_interval <= loop._max_interval

    def test_interval_caps_at_min(self, loop):
        loop.check_interval = loop._min_interval + 1
        anomalies = [{"type": "gc_pressure", "severity": "low"}]
        loop._adapt_interval({}, anomalies)
        assert loop.check_interval >= loop._min_interval


# ---------------------------------------------------------------------------
# _record_snapshot
# ---------------------------------------------------------------------------

class TestRecordSnapshot:
    def test_appends_to_history(self, loop):
        snapshot = {"timestamp": "2024-01-01T00:00:00"}
        loop._record_snapshot(snapshot, [])
        assert len(loop.health_history) == 1

    def test_history_contains_anomaly_count(self, loop):
        snapshot = {"timestamp": "t"}
        anomalies = [{"type": "gc_pressure", "severity": "low"}]
        loop._record_snapshot(snapshot, anomalies)
        assert loop.health_history[-1]["anomaly_count"] == 1

    def test_history_trimmed_to_max(self, loop):
        loop._max_history = 5
        for i in range(10):
            loop._record_snapshot({"timestamp": f"t{i}"}, [])
        assert len(loop.health_history) <= 5


# ---------------------------------------------------------------------------
# _self_heal (async)
# ---------------------------------------------------------------------------

class TestSelfHeal:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_gc_collect_on_memory_critical(self, loop):
        anomalies = [{"type": "memory_critical", "severity": "critical", "detail": "90%"}]
        snapshot = {}
        with patch("gc.collect") as mock_gc:
            self._run(loop._self_heal(anomalies, snapshot))
            mock_gc.assert_called()

    def test_heals_performed_incremented(self, loop):
        anomalies = [{"type": "gc_pressure", "severity": "low", "detail": "x"}]
        self._run(loop._self_heal(anomalies, {}))
        assert loop.heals_performed >= 1

    def test_optimizations_run_incremented(self, loop):
        anomalies = [{"type": "gc_pressure", "severity": "low", "detail": "x"}]
        initial = loop.optimizations_run
        self._run(loop._self_heal(anomalies, {}))
        assert loop.optimizations_run > initial

    def test_neurograph_self_heal_called(self, loop, mock_core):
        mock_ng = MagicMock()
        mock_core.neurograph = mock_ng
        loop.core = mock_core
        anomalies = [{"type": "graph_unhealthy", "severity": "medium", "detail": "broken"}]
        self._run(loop._self_heal(anomalies, {}))
        mock_ng.self_heal.assert_called_once()

    def test_missing_files_logs_without_crash(self, loop):
        anomalies = [{"type": "missing_files", "severity": "high", "detail": ["foo.py"]}]
        # Should not raise
        self._run(loop._self_heal(anomalies, {}))

    def test_heal_exception_does_not_propagate(self, loop, mock_core):
        mock_core.observe_performance.side_effect = RuntimeError("oops")
        anomalies = [{"type": "gc_pressure", "severity": "low", "detail": "x"}]
        # Should not raise
        self._run(loop._self_heal(anomalies, {}))
