# GhostGoat

GhostGoat currently supports one runtime: `main.py` starts the FastAPI service in
`config/api/server.py`, which uses the Agent Byte `AgentNetwork` for task
execution and the KnowledgeTank for knowledge search. The React dashboard is
optional and runs separately. This is an early-stage project, not a
production-grade autonomous or security platform.

---

## Supported Runtime

```
main.py
  └── config/api/server.py (FastAPI, port 8420)
        ├── AgentNetwork (agent_byte-master/agents/agent_network.py)
        │     ├── ResearchExecutor → KnowledgeTank search
        │     └── analysis TaskExecutor → Anthropic or explicit mock result
        ├── DecisionGovernor (policy checks)
        └── SQLite task/message state (.backend/runtime.sqlite3)

dashboard/ (optional Vite/React app, port 3000)
  └── reads the FastAPI endpoints; some monitoring charts remain simulated
```

Tasks without a configured provider may return a mock result; mock execution is
reported as unsuccessful and is not real completed work. Messages are recorded
as log-only and are not delivered to recipients.

### Runtime components

| Subsystem | What it does |
|-----------|-------------|
| **FastAPI server** | Supported HTTP runtime; API routes are limited to initialized components |
| **AgentNetwork** | Routes supported tasks to local knowledge research or analysis |
| **KnowledgeTank** | Existing knowledge store used for search and knowledge endpoints; it is not an autonomous ingestion pipeline |
| **DecisionGovernor** | Policy check used by the API for analyst task execution |
| **SQLite state** | Persists API task and message records across restarts |

---

## Installation

Supported install flow (Python 3.11+):

```bash
git clone <repo-url> GhostGoat
cd GhostGoat
pip install -e .            # core runtime
pip install -e ".[full]"    # core + all optional extras (ml, crypto, agents, pentest, dev)
```

See [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md) for individual extras. Legacy shell
wrappers (`.goat.sh`, `.install_ghostgoat.sh`, `install_upgrades.sh`, `merge_core.sh`,
`ghostgoat_shim.py`, `run_cognitive_system.py`) are compatibility-only and not part of
the supported path.

## Maturity and boundaries

| Area | Status |
|------|--------|
| `main.py` → `config/api/server.py` | **Supported runtime path** |
| `agent_byte-master/agents/agent_network.py` and `brain/knowledge/knowledge_tank.py` | **Used by the API**; other Agent Byte modules are not implied to be integrated |
| `dashboard/` | Optional UI; live views use API endpoints, while simulated charts/fallback records are labeled |
| `ACS_SYSTEM/` and `GFS/` | **Standalone experiments**; they do not protect, secure, or power the supported API runtime |
| `backend/` (Rust) and alternate launchers under `docs/scripts/`, `run_cognitive_system.py`, and `ghostgoat` | **Experimental/legacy**; not part of the supported runtime and not an API fallback |
| `vendor/`, custom agents, optional dependency extras | Not loaded by the supported API unless explicitly integrated |

---

## Running

`make` targets use the active Python (`PYTHON=... make run` to override); they wrap `python main.py`.

```bash
make run          # API (port 8420) + dashboard (port 3000)
make run-api      # API server only
make run-dash     # dashboard only
make test         # full pytest suite
make start        # full Docker stack (API + Redis + ChromaDB)
make start-full   # Docker stack + Neo4j + Ollama
```

Direct Python:

```bash
python main.py
python main.py --api-only
python main.py --dash-only
```

---

## Configuration

Create a `.env` file in the repo root. The current analyst executor uses
Anthropic directly; other provider variables are not wired into this runtime.

```bash
# Optional Anthropic credential; without it, analysis returns a mock result
ANTHROPIC_API_KEY=sk-ant-...
GHOSTGOAT_STATE_DB=.backend/runtime.sqlite3
GHOSTGOAT_KNOWLEDGE_PATH=.backend/knowledge_tank
```

API-only startup does not require Node.js. The dashboard requires Node.js 18+
and its dependencies.

---

## Project Structure

```
GhostGoat/
├── main.py                     # Supported supervisor entry point
├── config/api/server.py        # Supported FastAPI application
├── config/api/state_store.py   # SQLite persistence for API records
├── agent_byte-master/agents/   # AgentNetwork used by the API
├── agent_byte-master/brain/    # KnowledgeTank used by the API
├── dashboard/                  # Optional React/Vite client
├── ACS_SYSTEM/, GFS/            # Standalone experiments, not API security
├── backend/                     # Optional experimental Rust code
└── tests/                       # Python tests
```

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required |
| Node.js | 18+ | Dashboard only |
| Rust / cargo | stable | Backend scanner — optional |
| Docker | 20+ | Production stack — optional |
| Anthropic API key | — | Optional; analysis is reported as mock/failed without one |
