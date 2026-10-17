"""CTMS wiring: LLM-backed expansion via GhostGoat's gateway, with fallback."""

import asyncio

import pytest

from src.memory.ctms_wiring import StableExpander, _AsyncBridge, build_ctms_mapper
from src.memory.ctms_liquid import LiquidS4Expander


class FakeLLM:
    """Duck-typed gateway: same shape as LLMGateway (async complete)."""

    def __init__(self, reply: str = "wired consequence {n} ||| wired-ctx{n}", fail: bool = False):
        self.reply = reply
        self.fail = fail
        self.calls = 0

    async def complete(self, prompt: str, system=None) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("gateway down")
        return self.reply.format(n=self.calls)


def test_llm_expansion_builds_chain(tmp_path):
    llm = FakeLLM(reply="first consequence {n} ||| ctx-one")
    mapper = build_ctms_mapper(llm, tmp_path / "map.json", replica_id="test-replica")
    out = mapper.run("some concept", depth=3)
    assert "first consequence" in out and "ctx-one" in out
    assert llm.calls == 3  # one LLM call per expansion step
    assert len(mapper.state.nodes) == 4  # seed + 3 steps


def test_fallback_when_gateway_fails(tmp_path):
    llm = FakeLLM(fail=True)
    mapper = build_ctms_mapper(llm, tmp_path / "map.json", replica_id="test-replica")
    out = mapper.run("liquid s4", depth=3)
    # deterministic LiquidS4 fallback produced the chain instead of raising
    assert "adaptive sequence modeling architecture" in out
    assert len(mapper.state.nodes) == 4


def test_bridge_works_inside_running_event_loop(tmp_path):
    llm = FakeLLM(reply="inner-loop consequence ||| inner-ctx")
    mapper = build_ctms_mapper(llm, tmp_path / "map.json", replica_id="test-replica")

    async def caller():
        return mapper.run("concept", depth=2)  # sync call from inside a coroutine

    out = asyncio.run(caller())
    assert "inner-loop consequence" in out


def test_bridge_reuses_single_threaded_loop(tmp_path):
    llm = FakeLLM(reply="x ||| y")
    mapper = build_ctms_mapper(llm, tmp_path / "map.json", replica_id="test-replica")
    mapper.run("c1", depth=2)
    first_loop = mapper.expander.primary.complete._loop  # type: ignore[attr-defined]
    mapper.run("c2", depth=2)
    second_loop = mapper.expander.primary.complete._loop  # type: ignore[attr-defined]
    assert first_loop is second_loop  # one bridge loop for the mapper's lifetime


def test_stable_expander_never_raises():
    class Broken:
        def expand(self, seed, depth=10):
            raise ValueError("boom")

    chain = StableExpander(primary=Broken()).expand("concept", depth=2)
    assert chain and chain[0].context == "seed"


def test_rerun_after_outage_dedups(tmp_path):
    path = tmp_path / "map.json"
    ok_llm = FakeLLM(reply="stable consequence ||| s-ctx")
    mapper = build_ctms_mapper(ok_llm, path, replica_id="r1")
    mapper.run("concept", depth=2)
    healthy_count = len(mapper.state.nodes)

    # outage: a fresh mapper (e.g. after restart) falls back, adds fallback nodes
    down_llm = FakeLLM(fail=True)
    mapper2 = build_ctms_mapper(down_llm, path, replica_id="r1")
    mapper2.run("concept", depth=2)
    assert len(mapper2.state.nodes) > healthy_count  # fallback chain added

    # recovery: same content re-expands dedup back to no new duplicates
    before = len(mapper2.state.nodes)
    mapper3 = build_ctms_mapper(FakeLLM(reply="stable consequence ||| s-ctx"), path, replica_id="r1")
    mapper3.run("concept", depth=2)
    # seed + stable steps already exist; only identical content, so no explosion
    assert len(mapper3.state.nodes) <= before + 1


def test_orchestrator_registers_ctms_service(orchestrator):
    from run_cognitive_system import get_orchestrator

    orch = get_orchestrator()
    assert orch.ctms is not None
    assert "ctms" in orch.registry.list_services()
    assert isinstance(orch.ctms.expander, StableExpander)


@pytest.fixture
def orchestrator(tmp_path, monkeypatch):
    async def fake_complete(self, prompt, system=None):
        return "orch consequence ||| orch-ctx"

    from services.llm_gateway import LLMGateway

    monkeypatch.setattr(LLMGateway, "complete", fake_complete)
    from config.unified_config import (
        LLMConfig, LLMProvider, RuntimeConfig, TelegramConfig, UnifiedConfig,
    )
    import run_cognitive_system
    from run_cognitive_system import Orchestrator
    from services.telegram_bot import TelegramBotService  # noqa: F401

    config = UnifiedConfig(
        llm=LLMConfig(provider=LLMProvider.DEEPSEEK, model="test", api_key="key"),
        telegram=TelegramConfig(bot_token="", chat_ids=[], webhook_secret="s"),
        runtime=RuntimeConfig(data_dir=str(tmp_path)),
    )
    instance = Orchestrator(config)
    monkeypatch.setattr(run_cognitive_system, "_orchestrator", instance)
    return instance
