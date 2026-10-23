# GhostGoat

GhostGoat is a mixed-language repository centered on a Python orchestration runtime, with a significant Go and TypeScript footprint. The project combines a Python orchestrator and API surface with a TypeScript front-end and Go-based tooling/services.

## Language composition

Based on the current repository state, the codebase is dominated by the following language areas:

- Python (~9.7M): orchestrator runtime, API integration, agent logic, configuration, and service entry points
- Go (~4.5M): backend/system components and Go-based tooling
- TypeScript (~3.9M): dashboard and frontend application logic
- Supporting web and automation assets: HTML, CSS, JavaScript, Shell, Makefile, Rust, and Docker configuration

This mix reflects a hybrid architecture: Python drives the primary runtime, Go contributes backend/system code, and TypeScript powers the interactive dashboard experience.

GhostGoat is a single full runtime. `python main.py` boots one orchestrator
(`run_cognitive_system.py`) and serves the REST API, the Telegram service and
the dashboard from that same instance. There are no optional or fallback
startup paths: a missing LLM key, Node.js or dependency stops boot with an error.

---

## Supported Runtime

```
main.py (single entry point, one process)
  └── run_cognitive_system.py  Orchestrator (source of truth, service registry)
        ├── LLM gateway (config/unified_config.py provider; no mock provider)
        ├── DualBrain, KnowledgeTank, GraphRAG, NetworkedMemory, WorkflowEngine
        ├── AgentNetwork: shell, python, research, analyst, supervisor,
        │                 creative, analyzer, sentiment agents
        ├── Telegram service (agent_byte-master/services/telegram_bot.py)
        └── SQLite task/message state (.backend/runtime.sqlite3)
  ├── config/api/server.py  REST front end (port 8420), same orchestrator
  └── dashboard/ (port 3000), started in the same runtime loop
```

API: `GET /api/health`, `/api/agents`, `/api/graph`, `/api/memory`,
`POST /api/tasks` (`orchestrator.process_goal()`), `POST /api/telegram/webhook`.
Messages are recorded as log-only and are not delivered to recipients.

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
wrappers (`.goat.sh`, `.install_ghostgoat.sh`) are compatibility-only and not part of
the supported path.

## Maturity and boundaries

| Area | Status |
|------|--------|
| `main.py`, `run_cognitive_system.py`, `config/api/server.py`, `config/unified_config.py` | **Canonical runtime** |
| `agent_byte-master/` (agents, brain, core, services) | **Active subsystem layer**, registered by the orchestrator |
| `dashboard/` | UI started by `main.py` |
| `experimental/`, `ACS_SYSTEM/`, `GFS/`, `backend/` (Rust), `vendor/` | **Archive only**; never imported by the runtime |

---

## Running

`make` targets use the active Python (`PYTHON=... make run` to override); they wrap `python main.py`.

```bash
make run          # full runtime: orchestrator, API (8420), Telegram, dashboard (3000)
make test         # full pytest suite
make start        # full Docker stack (API + Redis + ChromaDB)
make start-full   # Docker stack + Neo4j + Ollama
```

Direct Python: `python main.py`

---

## Configuration

All settings load through `config/unified_config.py`. Create a `.env` file in the repo root:

```bash
LLM_PROVIDER=anthropic            # openai | anthropic | gemini | deepseek | ollama | local
ANTHROPIC_API_KEY=sk-ant-...      # key for the selected provider (required except ollama/local)
TELEGRAM_BOT_TOKEN=               # connects the Telegram transport
TELEGRAM_CHAT_ID=                 # allowed chat IDs, comma-separated
TELEGRAM_WEBHOOK_URL=             # optional; long polling when unset
TELEGRAM_WEBHOOK_SECRET=
GHOSTGOAT_HOST=127.0.0.1
GHOSTGOAT_PORT=8420
GHOSTGOAT_DATA_DIR=.backend
```

Boot requires Node.js 18+ for the dashboard. See
`agent_byte-master/services/README.md` for the Telegram flow.

---

## Project Structure

```
GhostGoat/
├── main.py                     # Single startup entry point
├── config/api/server.py        # Supported FastAPI application
├── config/api/state_store.py   # SQLite persistence for API records
├── agent_byte-master/agents/   # AgentNetwork used by the API
├── agent_byte-master/brain/    # KnowledgeTank used by the API
├── dashboard/                  # React/Vite dashboard started by main.py
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
| LLM provider API key | — | Required (not needed for ollama/local) |
