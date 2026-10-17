"""End-to-end tests: REST API, Telegram and agents share one real orchestrator."""

import asyncio

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

import run_cognitive_system
import config.api.server as server
from config.unified_config import (
    LLMConfig, LLMProvider, RuntimeConfig, TelegramConfig, UnifiedConfig,
)
from run_cognitive_system import Orchestrator
from services.llm_gateway import LLMGateway


@pytest.fixture
def orchestrator(tmp_path, monkeypatch):
    async def fake_complete(self, prompt, system=None):
        return f"handled: {prompt}"

    monkeypatch.setattr(LLMGateway, "complete", fake_complete)
    config = UnifiedConfig(
        llm=LLMConfig(provider=LLMProvider.DEEPSEEK, model="test", api_key="key"),
        telegram=TelegramConfig(bot_token="token", chat_ids=["42"], webhook_secret="s3cret"),
        runtime=RuntimeConfig(data_dir=str(tmp_path)),
    )
    instance = Orchestrator(config)
    sent = []

    async def fake_call(method, payload, timeout=15):
        if method == "getUpdates":
            await asyncio.sleep(0.05)
            return {"ok": True, "result": []}
        sent.append((method, payload))
        return {"ok": True}

    monkeypatch.setattr(instance.telegram, "_call", fake_call)
    instance.sent = sent
    monkeypatch.setattr(run_cognitive_system, "_orchestrator", instance)
    return instance


@pytest.fixture
def client(orchestrator):
    with TestClient(server.app) as test_client:
        yield test_client


def test_health_reports_runtime_status(client, orchestrator):
    body = client.get("/api/health").json()
    assert body["status"] == "online"
    assert body["modules"]["graphrag"] is True
    assert all(body["services"].values())
    assert {"orchestrator", "telegram", "sentiment", "creative", "analyzer"} <= body["services"].keys()


def test_all_agents_are_registered_at_startup(client):
    body = client.get("/api/agents").json()
    ids = {agent["id"] for agent in body["agents"]}
    assert {"shell-1", "research-1", "analyst-1", "creative-1", "analyzer-1", "sentiment-1"} <= ids
    assert {"id", "name", "type", "status", "capabilities", "tasks_completed"} <= body["agents"][0].keys()


def test_task_runs_through_orchestrator_and_updates_shared_state(client, orchestrator):
    task = client.post("/api/tasks", json={"description": "Analyze this request"}).json()["task"]
    assert task["status"] == "completed"
    assert task["agent"] == "analyst-1"
    assert task["execution_mode"] == "live"
    assert client.get("/api/tasks").json()["tasks"][0]["id"] == task["id"]
    assert client.get("/api/memory").json()["networked"]["long_term_entries"] == 1
    graph = client.get("/api/graph").json()
    assert {"task", "agent"} <= set(graph["stats"]["node_types"])
    assert graph["edges"][0]["type"] == "executed"
    assert orchestrator.knowledge_tank.get_stats()["total_entries"] == 1


def test_failed_provider_call_is_reported_not_mocked(client, monkeypatch):
    async def failing(self, prompt, system=None):
        raise RuntimeError("provider down")

    monkeypatch.setattr(LLMGateway, "complete", failing)
    task = client.post("/api/tasks", json={"description": "Analyze this request"}).json()["task"]
    assert task["status"] == "failed"
    assert task["execution_mode"] == "error"
    assert "provider down" in task["result"]["error"]


def test_research_results_are_not_reingested(client, orchestrator):
    task = client.post("/api/tasks", json={"description": "Research the knowledge store"}).json()["task"]
    assert task["agent"] == "research-1"
    assert orchestrator.knowledge_tank.get_stats()["total_entries"] == 0


def test_policy_blocks_external_execution(client, orchestrator, monkeypatch):
    monkeypatch.setattr(orchestrator, "decision_governor", lambda context: False)
    task = client.post("/api/tasks", json={"description": "Analyze this request"}).json()["task"]
    assert task["status"] == "failed"
    assert task["execution_mode"] == "blocked"
    assert client.get("/api/governance/policies").json()["audit_log"][0]["result"] == "blocked"


def test_message_is_persisted_as_log_not_delivered(client):
    message = client.post("/api/messages", json={
        "from_agent": "agent-a", "to_agent": "agent-b", "content": "hello",
    }).json()
    assert message["delivery"] == "log_only"
    assert client.get("/api/messages").json()["messages"][0]["id"] == message["id"]


def test_telegram_webhook_routes_goal_to_the_same_orchestrator(client, orchestrator):
    headers = {"X-Telegram-Bot-Api-Secret-Token": "s3cret"}
    update = {"message": {"chat": {"id": 42}, "text": "/goal Research the store"}}
    body = client.post("/api/telegram/webhook", json=update, headers=headers).json()
    assert body["reply"]
    assert orchestrator.sent[-1][1]["chat_id"] == 42
    assert orchestrator.telegram.conversations["42"][0]["status"] == "completed"
    tasks = client.get("/api/tasks").json()
    assert tasks["count"] == 1 and tasks["tasks"][0]["id"] == orchestrator.telegram.conversations["42"][0]["task_id"]


def test_telegram_webhook_plain_text_chats_without_creating_a_task(client, orchestrator):
    headers = {"X-Telegram-Bot-Api-Secret-Token": "s3cret"}
    update = {"message": {"chat": {"id": 42}, "text": "just saying hi"}}
    body = client.post("/api/telegram/webhook", json=update, headers=headers).json()
    assert "handled" in body["reply"]  # fake LLM: "handled: {prompt}"
    assert orchestrator.sent[-1][1]["chat_id"] == 42
    assert client.get("/api/tasks").json()["count"] == 0
    assert "42" not in orchestrator.telegram.conversations


def test_telegram_reports_api_task_events(client, orchestrator):
    client.post("/api/tasks", json={"description": "Analyze this request"})
    texts = [payload["text"] for method, payload in orchestrator.sent if method == "sendMessage"]
    # task events are formatted content-first: the result body, banner only as fallback
    assert "handled: Analyze this request" in texts
    assert any(text.startswith("Memory updated") for text in texts)
    assert any(text.startswith("Graph updated") for text in texts)


def test_telegram_webhook_rejects_bad_secret_and_unknown_chat(client, orchestrator):
    update = {"message": {"chat": {"id": 42}, "text": "hi"}}
    assert client.post("/api/telegram/webhook", json=update).status_code == 403
    headers = {"X-Telegram-Bot-Api-Secret-Token": "s3cret"}
    other = {"message": {"chat": {"id": 7}, "text": "hi"}}
    assert client.post("/api/telegram/webhook", json=other, headers=headers).json()["reply"] is None
    assert not [p for m, p in orchestrator.sent if m == "sendMessage" and p["chat_id"] == 7]


def test_telegram_status_command_reports_orchestrator(client, orchestrator):
    headers = {"X-Telegram-Bot-Api-Secret-Token": "s3cret"}
    update = {"message": {"chat": {"id": 42}, "text": "/agents"}}
    reply = client.post("/api/telegram/webhook", json=update, headers=headers).json()["reply"]
    assert "analyst-1" in reply


def test_mock_llm_provider_is_rejected():
    with pytest.raises(RuntimeError):
        LLMGateway(LLMConfig(provider=LLMProvider.MOCK))
