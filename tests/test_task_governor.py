"""TaskGovernor: rate limits, concurrency caps, daily budget, timeouts, stale sweep."""

import asyncio

import pytest

from core.governance.task_governor import TaskGovernor


def test_rate_limit_per_source():
    gov = TaskGovernor(max_concurrent=10, tasks_per_minute=2, daily_budget=0)
    assert gov.try_acquire("chat:1") == (True, "allowed")
    assert gov.try_acquire("chat:1") == (True, "allowed")
    assert gov.try_acquire("chat:1") == (False, "rate_limited")
    # different source has its own window
    assert gov.try_acquire("chat:2") == (True, "allowed")


def test_rate_window_slides():
    gov = TaskGovernor(max_concurrent=10, tasks_per_minute=1, daily_budget=0)
    assert gov.try_acquire("s")[0]
    assert not gov.try_acquire("s")[0]
    # age the recorded hits past the 60s window (deque: rebuild, no slicing)
    aged = [t - 61.0 for t in gov._windows["s"]]
    gov._windows["s"].clear()
    gov._windows["s"].extend(aged)
    assert gov.try_acquire("s")[0]


def test_daily_budget_and_rollover():
    gov = TaskGovernor(max_concurrent=10, tasks_per_minute=0, daily_budget=2)
    assert gov.try_acquire("api")[0]
    gov.release(); gov.record_outcome()
    assert gov.try_acquire("api")[0]
    gov.release(); gov.record_outcome()
    blocked, reason = gov.try_acquire("api")
    assert not blocked and reason == "budget_exhausted"
    # next day resets
    gov._today = staticmethod(lambda: "2099-01-01")
    assert gov.try_acquire("api")[0]


def test_concurrency_cap_and_release():
    gov = TaskGovernor(max_concurrent=1, tasks_per_minute=0, daily_budget=0)
    assert gov.try_acquire("a")[0]
    blocked, reason = gov.try_acquire("b")
    assert not blocked and reason == "busy"
    gov.release()
    assert gov.try_acquire("b")[0]
    assert gov.stats()["running"] == 1  # a released, only b running


def test_find_stale():
    tasks = [{"id": "1", "status": "running"}, {"id": "2", "status": "completed"},
             {"id": "3", "status": "running"}]
    assert [t["id"] for t in TaskGovernor.find_stale(tasks)] == ["1", "3"]


@pytest.fixture
def orchestrator(tmp_path, monkeypatch):
    async def fake_complete(self, prompt, system=None):
        return "ok"

    from services.llm_gateway import LLMGateway

    monkeypatch.setattr(LLMGateway, "complete", fake_complete)
    from config.unified_config import (
        LLMConfig, LLMProvider, RuntimeConfig, TelegramConfig, UnifiedConfig,
    )
    import run_cognitive_system
    from run_cognitive_system import Orchestrator

    config = UnifiedConfig(
        llm=LLMConfig(provider=LLMProvider.DEEPSEEK, model="test", api_key="key"),
        telegram=TelegramConfig(bot_token="", chat_ids=[], webhook_secret="s"),
        runtime=RuntimeConfig(data_dir=str(tmp_path)),
    )
    instance = Orchestrator(config)
    monkeypatch.setattr(run_cognitive_system, "_orchestrator", instance)
    return instance


def test_budget_blocks_second_goal_and_creates_no_task(orchestrator):
    orch = orchestrator
    orch.governor = TaskGovernor(max_concurrent=5, tasks_per_minute=0, daily_budget=1)

    async def fake_dispatch(agent_id, payload):
        return {"success": True, "result": "done"}

    orch.network.dispatch = fake_dispatch

    async def run():
        first = await orch.process_goal("goal one")
        tasks_after_first = len(orch.state_store.list_tasks())
        second = await orch.process_goal("goal two")
        return first, second, tasks_after_first

    first, second, tasks_after_first = asyncio.run(run())
    assert first["status"] == "completed"
    assert second["status"] == "budget_exhausted"
    assert second["id"] is None
    # rejected goal left no task record and no thought root
    assert len(orch.state_store.list_tasks()) == tasks_after_first


def test_task_timeout_enforced_and_slot_released(orchestrator):
    orch = orchestrator
    orch.governor = TaskGovernor(max_concurrent=2, tasks_per_minute=0,
                                 daily_budget=0, task_timeout=1)

    async def slow_dispatch(agent_id, payload):
        await asyncio.sleep(30)
        return {"success": True}

    orch.network.dispatch = slow_dispatch

    async def run():
        return await orch.process_goal("hangs forever")

    entry = asyncio.run(run())
    assert entry["status"] == "failed"
    assert entry["execution_mode"] == "timeout"
    assert "timed out" in entry["result"]["error"]
    # concurrency slot was released despite the timeout
    assert orch.governor.stats()["running"] == 0


def test_stale_sweep_on_restart(orchestrator):
    orch = orchestrator
    orch.state_store.save_task({"id": "task-old", "status": "running", "description": "x"})
    orch.state_store.save_task({"id": "task-ok", "status": "completed", "description": "y"})
    orch._sweep_stale_tasks()
    tasks = {t["id"]: t for t in orch.state_store.list_tasks()}
    assert tasks["task-old"]["status"] == "failed"
    assert tasks["task-old"]["execution_mode"] == "interrupted"
    assert tasks["task-ok"]["status"] == "completed"


def test_telegram_formats_governed_statuses():
    from services.telegram_bot import TelegramBotService

    assert "busy" in TelegramBotService.format_task({"status": "busy"}).lower()
    assert "budget" in TelegramBotService.format_task({"status": "budget_exhausted"}).lower()


def test_allow_chat_has_own_rate_window():
    gov = TaskGovernor(max_concurrent=1, tasks_per_minute=1, daily_budget=0)
    gov.chats_per_minute = 2
    assert gov.allow_chat("chat:1")
    assert gov.allow_chat("chat:1")
    assert not gov.allow_chat("chat:1")          # window exhausted
    assert gov.allow_chat("chat:2")              # separate per-chat window
    # task admission unaffected by chat usage and vice versa
    assert gov.try_acquire("chat:1")[0]


def test_allow_chat_unlimited_when_zero():
    gov = TaskGovernor(max_concurrent=1, tasks_per_minute=0, daily_budget=0)
    gov.chats_per_minute = 0
    assert all(gov.allow_chat("chat:x") for _ in range(50))


def test_stats_report_chat_window():
    gov = TaskGovernor()
    gov.chats_per_minute = 7
    assert gov.stats()["chats_per_minute"] == 7


def test_chat_for_telegram_creates_no_task_records(orchestrator):
    orch = orchestrator
    captured = {}

    async def fake_complete(prompt, system=None):
        captured["prompt"] = prompt
        captured["system"] = system
        return "hi there"

    orch.llm.complete = fake_complete
    before = len(orch.state_store.list_tasks())
    reply = asyncio.run(orch._chat_for_telegram("111", "hello", []))
    assert reply == "hi there"
    # no task record, no thought root, no governor slot taken
    assert len(orch.state_store.list_tasks()) == before
    assert orch.governor.stats()["running"] == 0
    assert "hello" in captured["prompt"]


def test_chat_for_telegram_rate_limited_returns_none(orchestrator):
    orch = orchestrator
    orch.governor.chats_per_minute = 1

    async def fake_complete(prompt, system=None):
        return "x"

    orch.llm.complete = fake_complete
    assert asyncio.run(orch._chat_for_telegram("7", "a", [])) == "x"
    assert asyncio.run(orch._chat_for_telegram("7", "b", [])) is None
