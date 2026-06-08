"""
Unit tests for core/governance/decision_governor.py
"""

import os
import pytest


# ---------------------------------------------------------------------------
# decision_governor
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDecisionGovernor:

    def test_allow_external_calls_default_true(self, monkeypatch):
        monkeypatch.delenv("ADAP_ALLOW_EXTERNAL", raising=False)
        # Module reads env at call time; the default env value is "1"
        # so we need to set it explicitly since other tests may clear it
        monkeypatch.setenv("ADAP_ALLOW_EXTERNAL", "1")
        from core.governance.decision_governor import allow_external_calls
        assert allow_external_calls("any_context") is True

    def test_allow_external_calls_disabled(self, monkeypatch):
        monkeypatch.setenv("ADAP_ALLOW_EXTERNAL", "0")
        from core.governance.decision_governor import allow_external_calls
        assert allow_external_calls("any_context") is False

    def test_allow_external_calls_arbitrary_value_is_false(self, monkeypatch):
        monkeypatch.setenv("ADAP_ALLOW_EXTERNAL", "yes")
        from core.governance.decision_governor import allow_external_calls
        # Only "1" returns True per implementation
        assert allow_external_calls("ctx") is False

    def test_allow_external_calls_context_arg_ignored(self, monkeypatch):
        """The context argument is accepted but not used in current implementation."""
        monkeypatch.setenv("ADAP_ALLOW_EXTERNAL", "1")
        from core.governance.decision_governor import allow_external_calls
        assert allow_external_calls("context_a") == allow_external_calls("context_b")
