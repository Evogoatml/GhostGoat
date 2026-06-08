"""
Unit tests for frameworks/agents/registry.py
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_available_cls(name="mock_fw"):
    """Return a mock AgentFramework class whose instances report available=True."""
    cls = MagicMock()
    instance = MagicMock()
    instance.available.return_value = True
    cls.return_value = instance
    return cls


def _make_unavailable_cls():
    """Return a mock AgentFramework class whose instances report available=False."""
    cls = MagicMock()
    instance = MagicMock()
    instance.available.return_value = False
    cls.return_value = instance
    return cls


def _make_broken_cls():
    """Return a mock AgentFramework class that raises on instantiation."""
    cls = MagicMock(side_effect=ImportError("library not installed"))
    return cls


# ---------------------------------------------------------------------------
# list_frameworks
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestListFrameworks:

    def test_returns_dict(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        registry._BACKENDS["alpha"] = _make_available_cls()
        registry._BACKENDS["beta"] = _make_unavailable_cls()
        result = registry.list_frameworks()
        assert isinstance(result, dict)
        assert "alpha" in result
        assert "beta" in result
        registry._BACKENDS.clear()

    def test_available_backend_returns_true(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        registry._BACKENDS["good"] = _make_available_cls()
        result = registry.list_frameworks()
        assert result["good"] is True
        registry._BACKENDS.clear()

    def test_unavailable_backend_returns_false(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        registry._BACKENDS["bad"] = _make_unavailable_cls()
        result = registry.list_frameworks()
        assert result["bad"] is False
        registry._BACKENDS.clear()

    def test_broken_backend_returns_false(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        registry._BACKENDS["broken"] = _make_broken_cls()
        result = registry.list_frameworks()
        assert result["broken"] is False
        registry._BACKENDS.clear()


# ---------------------------------------------------------------------------
# get_framework
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetFramework:

    def test_get_known_available_framework(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        cls = _make_available_cls()
        registry._BACKENDS["myfx"] = cls
        fw = registry.get_framework("myfx")
        assert fw.available() is True
        registry._BACKENDS.clear()

    def test_get_unknown_framework_raises_value_error(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        with pytest.raises(ValueError, match="Unknown agent framework"):
            registry.get_framework("nonexistent_xyz")
        registry._BACKENDS.clear()

    def test_get_unavailable_framework_raises_runtime_error(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        registry._BACKENDS["notinstalled"] = _make_unavailable_cls()
        with pytest.raises(RuntimeError, match="not installed"):
            registry.get_framework("notinstalled")
        registry._BACKENDS.clear()

    def test_auto_select_first_available(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        registry._BACKENDS["broken"] = _make_broken_cls()
        cls = _make_available_cls()
        registry._BACKENDS["good"] = cls
        fw = registry.get_framework()
        assert fw.available() is True
        registry._BACKENDS.clear()

    def test_auto_select_no_available_raises_runtime_error(self):
        from frameworks.agents import registry
        registry._BACKENDS.clear()
        registry._BACKENDS["bad1"] = _make_unavailable_cls()
        registry._BACKENDS["bad2"] = _make_broken_cls()
        with pytest.raises(RuntimeError, match="No agent framework installed"):
            registry.get_framework()
        registry._BACKENDS.clear()


# ---------------------------------------------------------------------------
# AgentSpec / TaskSpec / RunResult dataclasses
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBaseDataclasses:

    def test_agent_spec_defaults(self):
        from frameworks.agents.base import AgentSpec
        spec = AgentSpec(name="bot", role="worker", goal="do stuff")
        assert spec.backstory == ""
        assert spec.tools == []
        assert spec.llm_model is None
        assert spec.extra == {}

    def test_task_spec_defaults(self):
        from frameworks.agents.base import TaskSpec
        spec = TaskSpec(description="summarize this")
        assert spec.expected_output == ""
        assert spec.agent_name is None
        assert spec.context == {}

    def test_run_result_defaults(self):
        from frameworks.agents.base import RunResult
        result = RunResult(output="done")
        assert result.raw is None
        assert result.metadata == {}
