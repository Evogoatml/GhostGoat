"""
Tests for api/server.py — FastAPI endpoints.
Uses TestClient so no real server is needed.
"""

import pytest
from unittest.mock import MagicMock, patch

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — mock heavy module-level imports before importing the app
# ---------------------------------------------------------------------------

def _make_app():
    """Import the app with all heavy deps mocked out."""
    mocks = {
        "psutil": MagicMock(),
        "uvicorn": MagicMock(),
    }
    with patch.dict("sys.modules", mocks):
        # Patch module-level side-effectful calls
        with patch("api.server._try_import", return_value=None), \
             patch("api.server._load_orchestrator"):
            import importlib
            import api.server as srv
            importlib.reload(srv)
            return srv


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Return a TestClient bound to the FastAPI app."""
    import sys
    psutil_mock = MagicMock()
    psutil_mock.cpu_percent.return_value = 10.0
    mem = MagicMock()
    mem.percent = 40.0
    mem.used = 2 * 1024 ** 3
    mem.total = 8 * 1024 ** 3
    psutil_mock.virtual_memory.return_value = mem
    disk = MagicMock()
    disk.percent = 55.0
    psutil_mock.disk_usage.return_value = disk
    psutil_mock.pids.return_value = list(range(100))

    with patch.dict(sys.modules, {"psutil": psutil_mock, "uvicorn": MagicMock()}):
        with patch("api.server._try_import", return_value=None), \
             patch("api.server._load_orchestrator"):
            import importlib
            import api.server as srv
            importlib.reload(srv)
            # Reset module-level globals
            srv.service_registry = None
            srv.decision_governor = None
            srv.task_handler_mod = None
            srv.efficiency_engine = None
            srv.knowledge_tank_mod = None
            srv.orchestrator_instance = None
            srv.nanoagent_spawner = None
            srv.tool_registry = None
            srv._task_log.clear()
            srv._message_log.clear()
            srv._governance_log.clear()
            yield TestClient(srv.app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_status_online(self, client):
        data = client.get("/api/health").json()
        assert data["status"] == "online"

    def test_health_has_uptime(self, client):
        data = client.get("/api/health").json()
        assert "uptime" in data
        assert isinstance(data["uptime"], float)

    def test_health_has_modules(self, client):
        data = client.get("/api/health").json()
        assert "modules" in data
        modules = data["modules"]
        expected_keys = {
            "service_registry", "decision_governor", "task_handler",
            "efficiency_engine", "knowledge_tank", "orchestrator"
        }
        assert expected_keys.issubset(modules.keys())

    def test_health_modules_false_when_not_loaded(self, client):
        data = client.get("/api/health").json()
        for v in data["modules"].values():
            assert v is False


# ---------------------------------------------------------------------------
# System metrics endpoint
# ---------------------------------------------------------------------------

class TestSystemMetrics:
    def test_metrics_returns_200(self, client):
        resp = client.get("/api/system/metrics")
        assert resp.status_code == 200

    def test_metrics_has_required_fields(self, client):
        data = client.get("/api/system/metrics").json()
        for field in ("cpu_percent", "memory_percent", "memory_used_mb",
                      "memory_total_mb", "disk_percent", "process_count", "timestamp"):
            assert field in data, f"Missing field: {field}"

    def test_metrics_cpu_is_number(self, client):
        data = client.get("/api/system/metrics").json()
        assert isinstance(data["cpu_percent"], (int, float))


# ---------------------------------------------------------------------------
# Agents endpoint
# ---------------------------------------------------------------------------

class TestAgentsEndpoint:
    def test_list_agents_returns_200(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200

    def test_list_agents_has_agents_key(self, client):
        data = client.get("/api/agents").json()
        assert "agents" in data
        assert "count" in data

    def test_list_agents_count_matches_list(self, client):
        data = client.get("/api/agents").json()
        assert data["count"] == len(data["agents"])

    def test_builtin_agents_included(self, client):
        data = client.get("/api/agents").json()
        names = [a["name"] for a in data["agents"]]
        assert "Brain Core" in names

    def test_agents_have_required_fields(self, client):
        data = client.get("/api/agents").json()
        for agent in data["agents"]:
            assert "id" in agent
            assert "name" in agent
            assert "status" in agent


# ---------------------------------------------------------------------------
# Tasks endpoint
# ---------------------------------------------------------------------------

class TestTasksEndpoint:
    def test_list_tasks_returns_200(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200

    def test_list_tasks_empty_initially(self, client):
        import api.server as srv
        srv._task_log.clear()
        data = client.get("/api/tasks").json()
        assert data["tasks"] == []
        assert data["count"] == 0

    def test_create_task_no_handler(self, client):
        import api.server as srv
        srv._task_log.clear()
        resp = client.post("/api/tasks", json={"description": "test task"})
        assert resp.status_code == 200
        data = resp.json()
        assert "task" in data
        assert data["task"]["description"] == "test task"
        assert data["task"]["status"] in ("failed", "running", "completed")

    def test_create_task_default_priority(self, client):
        import api.server as srv
        srv._task_log.clear()
        resp = client.post("/api/tasks", json={"description": "priority test"})
        assert resp.status_code == 200
        assert resp.json()["task"]["priority"] == 5

    def test_create_task_custom_priority(self, client):
        import api.server as srv
        srv._task_log.clear()
        resp = client.post("/api/tasks", json={"description": "urgent", "priority": 1})
        assert resp.status_code == 200
        assert resp.json()["task"]["priority"] == 1

    def test_created_task_appears_in_list(self, client):
        import api.server as srv
        srv._task_log.clear()
        client.post("/api/tasks", json={"description": "list me"})
        data = client.get("/api/tasks").json()
        assert data["count"] >= 1


# ---------------------------------------------------------------------------
# Messages endpoint
# ---------------------------------------------------------------------------

class TestMessagesEndpoint:
    def test_list_messages_empty(self, client):
        import api.server as srv
        srv._message_log.clear()
        data = client.get("/api/messages").json()
        assert data["messages"] == []

    def test_send_message(self, client):
        import api.server as srv
        srv._message_log.clear()
        payload = {
            "from_agent": "agent-a",
            "to_agent": "agent-b",
            "content": "hello",
            "type": "task_assign",
        }
        resp = client.post("/api/messages", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["from"] == "agent-a"
        assert data["to"] == "agent-b"
        assert data["status"] == "delivered"

    def test_sent_message_appears_in_list(self, client):
        import api.server as srv
        srv._message_log.clear()
        client.post("/api/messages", json={
            "from_agent": "x", "to_agent": "y", "content": "hi"
        })
        data = client.get("/api/messages").json()
        assert data["count"] >= 1

    def test_message_has_id(self, client):
        resp = client.post("/api/messages", json={
            "from_agent": "x", "to_agent": "y", "content": "test"
        })
        assert "id" in resp.json()


# ---------------------------------------------------------------------------
# Governance endpoints
# ---------------------------------------------------------------------------

class TestGovernanceEndpoint:
    def test_get_policies_no_governor(self, client):
        import api.server as srv
        srv.decision_governor = None
        srv._governance_log.clear()
        data = client.get("/api/governance/policies").json()
        assert data["policies"] == []

    def test_check_policy_no_governor_503(self, client):
        import api.server as srv
        srv.decision_governor = None
        resp = client.post("/api/governance/check")
        assert resp.status_code == 503

    def test_check_policy_with_governor(self, client):
        import api.server as srv
        mock_gov = MagicMock()
        mock_gov.allow_external_calls.return_value = True
        srv.decision_governor = mock_gov
        srv._governance_log.clear()
        resp = client.post("/api/governance/check", params={"context": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] in ("allowed", "blocked")
        srv.decision_governor = None


# ---------------------------------------------------------------------------
# Services endpoint
# ---------------------------------------------------------------------------

class TestServicesEndpoint:
    def test_services_no_registry(self, client):
        import api.server as srv
        srv.service_registry = None
        data = client.get("/api/services").json()
        assert "error" in data

    def test_services_with_registry(self, client):
        import api.server as srv
        mock_reg = MagicMock()
        mock_reg.list_services.return_value = {"svc1": True, "svc2": False}
        srv.service_registry = mock_reg
        data = client.get("/api/services").json()
        assert "services" in data
        assert "svc1" in data["services"]
        srv.service_registry = None


# ---------------------------------------------------------------------------
# Knowledge endpoint
# ---------------------------------------------------------------------------

class TestKnowledgeEndpoint:
    def test_search_no_tank(self, client):
        import api.server as srv
        srv.knowledge_tank_mod = None
        data = client.get("/api/knowledge/search", params={"q": "test"}).json()
        assert data["results"] == []
        assert "error" in data


# ---------------------------------------------------------------------------
# Tools endpoint
# ---------------------------------------------------------------------------

class TestToolsEndpoint:
    def test_list_tools_no_registry(self, client):
        import api.server as srv
        srv.tool_registry = None
        data = client.get("/api/tools").json()
        assert "error" in data

    def test_execute_tool_no_registry_503(self, client):
        import api.server as srv
        srv.tool_registry = None
        resp = client.post("/api/tools/execute", params={"name": "mytool"})
        assert resp.status_code == 503

    def test_execute_tool_with_registry(self, client):
        import api.server as srv
        mock_reg = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "done"
        mock_result.error = None
        mock_reg.execute_tool.return_value = mock_result
        srv.tool_registry = mock_reg
        resp = client.post("/api/tools/execute", params={"name": "mytool"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool"] == "mytool"
        assert data["success"] is True
        srv.tool_registry = None


# ---------------------------------------------------------------------------
# Nanoagents endpoint
# ---------------------------------------------------------------------------

class TestNanoagentsEndpoint:
    def test_list_nanoagents_no_spawner(self, client):
        import api.server as srv
        srv.nanoagent_spawner = None
        data = client.get("/api/nanoagents").json()
        assert "error" in data

    def test_execute_nanoagent_no_spawner_503(self, client):
        import api.server as srv
        srv.nanoagent_spawner = None
        resp = client.post("/api/nanoagents/execute", json={"task_type": "system_info"})
        assert resp.status_code == 503

    def test_execute_nanoagent_with_spawner(self, client):
        import api.server as srv
        mock_spawner = MagicMock()
        mock_spawner.execute.return_value = {"result": "ok"}
        srv.nanoagent_spawner = mock_spawner
        resp = client.post("/api/nanoagents/execute", json={"task_type": "system_info"})
        assert resp.status_code == 200
        srv.nanoagent_spawner = None
