"""ThoughtStore adapter integration: orchestrator chain, agent hooks, authenticated API."""

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from core.base import BaseAgent
from src.memory.thought_adapter import ThoughtMemory
from src.memory.thought_store import ThoughtStore
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
        telegram=TelegramConfig(bot_token="", chat_ids=[], webhook_secret="s"),
        runtime=RuntimeConfig(data_dir=str(tmp_path)),
    )
    instance = Orchestrator(config)
    monkeypatch.setattr(run_cognitive_system, "_orchestrator", instance)
    return instance


@pytest.fixture
def client(orchestrator):
    with TestClient(server.app) as test_client:
        yield test_client


class EchoAgent(BaseAgent):
    name = "echo"

    def _build_command(self, task, context):
        return "echo"

    def request_execution(self, agent_id, command, target=None):
        return {"status": "ok", "stdout": "done"}


def test_adapter_links_tree_and_delta():
    mem = ThoughtMemory(ThoughtStore(":memory:"))
    root = mem.record("root", "goal")
    child = mem.record("step", "x", parent_id=root)
    assert mem.get(child)["root_id"] == root
    tree = mem.tree(root)
    assert [t["id"] for t in tree["thoughts"]] == [root, child]
    assert tree["links"] == [{"cause_id": root, "effect_id": child, "relation": "caused"}]
    assert [r["id"] for r in mem.roots()] == [root]
    assert len(mem.delta(mem.get(root)["seq"])) == 1


def test_agent_records_start_and_result():
    mem = ThoughtMemory(ThoughtStore(":memory:"))
    parent = mem.record("root", "goal")
    agent = EchoAgent()
    agent.thoughts = mem
    assert agent.execute("t", {"thought_id": parent}) == "done"
    assert [t["kind"] for t in mem.tree(parent)["thoughts"]] == ["root", "agent_start", "agent_result"]


def test_agent_without_adapter_unchanged():
    assert EchoAgent().execute("t") == "done"


def test_process_goal_writes_chain_and_api(client, orchestrator, monkeypatch):
    monkeypatch.setenv("GHOSTGOAT_API_KEY", "k3y")
    entry = client.post("/api/tasks", json={"description": "analyze risk"}).json()["task"]
    root_id = entry["thought_root_id"]
    h = {"X-API-Key": "k3y"}

    assert client.get("/api/thoughts/roots").status_code == 401
    assert client.get("/api/thoughts/roots", headers={"X-API-Key": "bad"}).status_code == 401
    assert root_id in [r["id"] for r in client.get("/api/thoughts/roots", headers=h).json()["roots"]]

    tree = client.get(f"/api/thoughts/roots/{root_id}/tree", headers=h).json()
    kinds = [t["kind"] for t in tree["thoughts"]]
    assert kinds[:2] == ["root", "task_created"] and kinds[-1] == "task_completed"
    assert client.get(f"/api/thoughts/{root_id}", headers=h).json()["id"] == root_id
    assert client.get("/api/thoughts/nope", headers=h).status_code == 404


def test_memory_api_disabled_without_key(client, monkeypatch):
    monkeypatch.delenv("GHOSTGOAT_API_KEY", raising=False)
    assert client.get("/api/thoughts/roots", headers={"X-API-Key": ""}).status_code == 503
