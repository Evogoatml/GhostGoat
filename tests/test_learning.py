"""
Unit tests for core/learning/learning_core.py and user_behavior.py
"""

import importlib
import json
import os
import pytest


@pytest.fixture()
def learning_module(tmp_path, monkeypatch):
    """Return the learning_core module with FILE redirected to tmp_path."""
    import core.learning.learning_core as lc
    monkeypatch.setenv("GHOSTGOAT_LEARNING_FILE", str(tmp_path / "task_memory.json"))
    importlib.reload(lc)
    return lc


@pytest.fixture()
def behavior_module(tmp_path, monkeypatch):
    """Return user_behavior module with FILE redirected to tmp_path."""
    import core.learning.user_behavior as ub
    monkeypatch.setenv("GHOSTGOAT_USER_BEHAVIOR_FILE", str(tmp_path / "user_behavior.json"))
    importlib.reload(ub)
    return ub


# ---------------------------------------------------------------------------
# learning_core
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLearningCore:

    def test_load_empty_when_no_file(self, learning_module):
        assert learning_module.load() == []

    def test_record_creates_file(self, learning_module, tmp_path):
        learning_module.record("task_a", "success")
        assert os.path.exists(str(tmp_path / "task_memory.json"))

    def test_record_appends_entry(self, learning_module):
        learning_module.record("task_b", "success")
        learning_module.record("task_b", "failure")
        data = learning_module.load()
        assert len(data) == 2

    def test_record_stores_correct_task(self, learning_module):
        learning_module.record("my_task", "success", metrics={"latency": 0.5})
        data = learning_module.load()
        assert data[0]["task"] == "my_task"
        assert data[0]["result"] == "success"
        assert data[0]["metrics"]["latency"] == 0.5

    def test_record_includes_timestamp(self, learning_module):
        learning_module.record("ts_task", "success")
        data = learning_module.load()
        assert "timestamp" in data[0]
        assert isinstance(data[0]["timestamp"], float)

    def test_summarize_no_records(self, learning_module):
        result = learning_module.summarize("unknown_task")
        assert "No records" in result

    def test_summarize_all_success(self, learning_module):
        for _ in range(3):
            learning_module.record("good_task", "success")
        result = learning_module.summarize("good_task")
        assert "3/3" in result

    def test_summarize_mixed(self, learning_module):
        learning_module.record("mixed", "success")
        learning_module.record("mixed", "failure")
        learning_module.record("mixed", "success")
        result = learning_module.summarize("mixed")
        assert "2/3" in result

    def test_summarize_all_failure(self, learning_module):
        learning_module.record("bad_task", "failure")
        learning_module.record("bad_task", "failure")
        result = learning_module.summarize("bad_task")
        assert "0/2" in result

    def test_load_persists_across_calls(self, learning_module):
        learning_module.record("persist_task", "success")
        data1 = learning_module.load()
        data2 = learning_module.load()
        assert data1 == data2


# ---------------------------------------------------------------------------
# user_behavior
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUserBehavior:

    def test_load_empty_when_no_file(self, behavior_module):
        assert behavior_module.load() == []

    def test_suggest_no_data(self, behavior_module):
        result = behavior_module.suggest()
        assert "No suggestions" in result

    def test_record_creates_entry(self, behavior_module):
        behavior_module.record("run tests", "success")
        data = behavior_module.load()
        assert len(data) == 1
        assert data[0]["command"] == "run tests"

    def test_suggest_most_frequent(self, behavior_module):
        behavior_module.record("deploy", "ok")
        behavior_module.record("test", "ok")
        behavior_module.record("deploy", "ok")
        behavior_module.record("deploy", "ok")
        result = behavior_module.suggest()
        assert "deploy" in result

    def test_suggest_tie_returns_one_of_them(self, behavior_module):
        behavior_module.record("cmd_a", "ok")
        behavior_module.record("cmd_b", "ok")
        result = behavior_module.suggest()
        assert "cmd_a" in result or "cmd_b" in result

    def test_record_stores_timestamp(self, behavior_module):
        behavior_module.record("ping", "pong")
        data = behavior_module.load()
        assert "time" in data[0]
        assert isinstance(data[0]["time"], float)
