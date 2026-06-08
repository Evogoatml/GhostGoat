#!/usr/bin/env python3
"""
GhostGoat Smoke Tests
Quick validation that core systems are working.
Refactored to use proper pytest assertions so failures are always caught.
"""

import asyncio
import os
import pytest

# Ensure test environment uses mock providers — no real API keys needed.
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("MEMORY_BACKEND", "memory")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_global_config():
    """Clear cached global config so env-var overrides take effect."""
    import config.unified_config as uc
    uc._config = None


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_imports():
    """Core modules can be imported without error."""
    from config.unified_config import init_config, LLMProvider, MemoryBackend  # noqa: F401
    from frameworks.llm.multi_llm import create_llm, LLMMessage, LLMResponse  # noqa: F401
    from core.brain.agents.base import GhostGoat, Task, RecursiveMemory  # noqa: F401


@pytest.mark.smoke
def test_config():
    """Configuration system initialises and serialises correctly."""
    _reset_global_config()

    from config.unified_config import init_config

    config = init_config()

    assert config is not None
    assert hasattr(config, "llm")
    assert hasattr(config, "memory")

    config_dict = config.to_dict()
    assert isinstance(config_dict, dict)
    assert "llm" in config_dict
    assert isinstance(config_dict["llm"]["provider"], str), "Enum not serialised to str"


@pytest.mark.smoke
def test_mock_llm():
    """Mock LLM generates a non-empty response."""
    from frameworks.llm.multi_llm import create_llm, LLMMessage
    from config.unified_config import LLMConfig, LLMProvider

    config = LLMConfig(provider=LLMProvider.MOCK)
    llm = create_llm(config)

    messages = [LLMMessage(role="user", content="Hello world")]
    response = asyncio.run(llm.generate(messages))

    assert response is not None
    assert hasattr(response, "content")
    assert len(response.content) > 0


@pytest.mark.smoke
def test_monitoring():
    """Monitoring system increments counters and reports a summary."""
    from frameworks.monitoring.monitoring import get_monitoring

    mon = get_monitoring()
    mon.metrics.increment("smoke_test_counter")
    mon.metrics.gauge("smoke_test_gauge", 42.0)

    summary = mon.metrics.get_summary()
    assert "counters" in summary
    assert "gauges" in summary


@pytest.mark.smoke
def test_ghostgoat_core():
    """GhostGoat core classes can be instantiated and used."""
    from core.brain.agents.base import GhostGoat, Task, RecursiveMemory

    # RecursiveMemory
    memory = RecursiveMemory()
    memory.add(level=0, data={"test": "hello"})
    results = memory.query("hello", top_k=3)
    assert len(results) > 0, "Memory query returned nothing"

    memory.update_knowledge({"entities": ["test_entity"], "insights": ["test_insight"]})
    assert len(memory.knowledge_graph["entities"]) == 1
    assert len(memory.knowledge_graph["insights"]) == 1

    # GhostGoat
    goat = GhostGoat()
    assert len(goat.agent_pools) > 0
    assert "coding" in goat.agent_pools

    # Task
    task = Task(description="Test task", domain="coding", context={"test": True})
    assert task.description == "Test task"


@pytest.mark.smoke
def test_filesystem(tmp_path):
    """Project can create directories in a temp location."""
    target = tmp_path / "data" / "test"
    target.mkdir(parents=True)
    assert target.is_dir()


# ---------------------------------------------------------------------------
# Allow running directly: python tests/smoke_test.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
