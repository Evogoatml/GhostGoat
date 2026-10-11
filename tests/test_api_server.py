"""End-to-end API tests for the canonical FastAPI runtime."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from config.api.state_store import RuntimeState
import config.api.server as server


class FakeKnowledgeTank:
    def __init__(self):
        self.entries = {
            "knowledge-1": SimpleNamespace(
                id="knowledge-1",
                category="task_result",
                content="Stored task result",
                tags=["analyst-1"],
                source="task-1",
                confidence=1.0,
                usage_count=0,
            )
        }
        self.ingested = []

    def search(self, query, limit=10):
        if not query or query.lower() in "stored task result":
            return [{
                "id": "knowledge-1",
                "category": "task_result",
                "content": "Stored task result",
                "tags": ["analyst-1"],
                "source": "task-1",
                "confidence": 1.0,
                "usage": 0,
            }][:limit]
        return []

    def ingest_bulk(self, records):
        self.ingested.extend(records)

    def get_stats(self):
        return {
            "total_entries": len(self.entries),
            "total_algorithms": 0,
            "storage_path": "test",
        }


class FakeNetwork:
    def __init__(self, *, mode="live", success=True):
        self.mode = mode
        self.success = success
        self.selected_agent = None
        self.profiles = {
            "analyst-1": SimpleNamespace(
                agent_id="analyst-1",
                name="analyst",
                role="analysis",
                status="idle",
                capabilities=["analyze"],
                total_tasks=0,
            ),
            "research-1": SimpleNamespace(
                agent_id="research-1",
                name="researcher",
                role="research",
                status="idle",
                capabilities=["search"],
                total_tasks=0,
            ),
        }

    def select_agent(self, goal):
        return "research-1" if "research" in goal.lower() or "search" in goal.lower() else "analyst-1"

    async def dispatch(self, agent_id, payload):
        self.selected_agent = agent_id
        return {
            "success": self.success,
            "result": f"handled: {payload['goal']}",
            "agent_id": agent_id,
            "execution_mode": self.mode,
        }


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "state_store", RuntimeState(tmp_path / "api.sqlite3"))
    monkeypatch.setattr(server, "knowledge_tank", FakeKnowledgeTank())
    monkeypatch.setattr(server, "orchestrator_instance", FakeNetwork())
    monkeypatch.setattr(server, "service_registry", None)
    monkeypatch.setattr(server, "decision_governor", lambda context: True)
    server._governance_log.clear()
    with TestClient(server.app) as test_client:
        yield test_client


def test_health_reports_initialized_runtime(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"
    assert body["modules"]["orchestrator"] is True
    assert body["modules"]["knowledge_tank"] is True


def test_api_agent_schema_matches_dashboard(client):
    body = client.get("/api/agents").json()
    assert body["count"] == 2
    agent = body["agents"][0]
    assert {"id", "name", "type", "status", "health", "cpu", "memory",
            "capabilities", "tasks_completed", "uptime"} <= agent.keys()
    assert agent["health"] is None


def test_task_dispatch_routes_research_and_persists(client):
    response = client.post("/api/tasks", json={"description": "Research the knowledge store"})
    task = response.json()["task"]
    assert task["status"] == "completed"
    assert task["agent"] == "research-1"
    assert task["execution_mode"] == "live"
    assert task["progress"] == 100
    assert client.get("/api/tasks").json()["tasks"][0]["id"] == task["id"]


def test_mock_execution_is_not_reported_as_completed(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(server, "orchestrator_instance", FakeNetwork(mode="mock", success=False))
    task = client.post("/api/tasks", json={"description": "Summarize this request"}).json()["task"]
    assert task["status"] == "failed"
    assert task["execution_mode"] == "mock"
    assert task["result"]["success"] is False


def test_policy_blocks_external_execution(client, monkeypatch):
    monkeypatch.setattr(server, "decision_governor", lambda context: False)
    task = client.post("/api/tasks", json={"description": "Analyze this request"}).json()["task"]
    assert task["status"] == "failed"
    assert task["execution_mode"] == "blocked"
    assert client.get("/api/governance/policies").json()["audit_log"][0]["result"] == "blocked"


def test_successful_task_result_is_ingested(client):
    tank = server.knowledge_tank
    client.post("/api/tasks", json={"description": "Analyze this request"})
    assert tank.ingested[0]["category"] == "task_result"
    assert tank.ingested[0]["source"].startswith("task-")


def test_message_is_persisted_as_log_not_delivered(client, tmp_path):
    message = client.post("/api/messages", json={
        "from_agent": "agent-a",
        "to_agent": "agent-b",
        "content": "hello",
    }).json()
    assert message["status"] == "logged"
    assert message["delivery"] == "log_only"
    assert client.get("/api/messages").json()["messages"][0]["id"] == message["id"]
    reopened = RuntimeState(tmp_path / "api.sqlite3")
    assert reopened.list_messages()[0]["id"] == message["id"]
    reopened.close()


def test_knowledge_and_memory_are_backed_by_store(client):
    assert client.get("/api/knowledge/search", params={"q": "stored"}).json()["count"] == 1
    assert client.get("/api/memory/search").json()["entries"][0]["id"] == "knowledge-1"
    graph = client.get("/api/knowledge/graph").json()
    assert graph["nodes"][0]["id"] == "knowledge-1"
    assert client.get("/api/memory/stats").json()["total_entries"] == 1


def test_unsupported_optional_integrations_are_not_exposed(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(path.startswith("/api/tools") for path in paths)
    assert not any(path.startswith("/api/nanoagents") for path in paths)
    assert not any(path.startswith("/api/posters") for path in paths)


def test_api_only_dependency_check_does_not_require_node(monkeypatch):
    import main

    def unexpected_node_check(*args, **kwargs):
        raise AssertionError("Node must not be checked for API-only startup")

    monkeypatch.setattr(main.subprocess, "run", unexpected_node_check)
    assert main.check_dependencies(require_dashboard=False) is True
