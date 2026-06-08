# GhostGoat

> **Autonomous multi-agent orchestration platform with self-assembly, self-healing, and post-quantum security.**

GhostGoat is a production-grade AI operating system that coordinates heterogeneous agent fleets across any domain — code generation, research synthesis, financial analysis, creative work, and more. It reasons, repairs, and evolves itself without operator intervention, while enforcing cryptographic governance at every boundary.

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                        GhostGoat                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  LLM Layer   │  │  Agent Fleet │  │   Memory Core    │  │
│  │  Claude      │  │  Specialist  │  │  Semantic search │  │
│  │  OpenAI      │──│  pools per   │──│  Graph reasoning │  │
│  │  Gemini      │  │  domain      │  │  KnowledgeTank   │  │
│  │  Mock (dev)  │  │              │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│           │                │                   │            │
│  ┌────────▼────────────────▼───────────────────▼─────────┐  │
│  │                  Orchestrator                          │  │
│  │   BuildLoop (self-assembly) · SelfAwareLoop (healing)  │  │
│  │   DecisionGovernor (policy) · Sandbox (isolation)      │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────────────▼───────────────────────────────┐  │
│  │              ACS Security Layer                        │  │
│  │   CRYSTALS-Kyber KEM · Dilithium signatures            │  │
│  │   Adaptive cipher pipeline · Audit log signing         │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │ FastAPI (port 8420)       │ React dashboard (port 3000)
```

### Core subsystems

| Subsystem | What it does |
|-----------|-------------|
| **LLM Orchestrator** | Unified adapter for Claude, OpenAI, Gemini, or mock; failover and retry built in |
| **BuildLoop** | Reads the architectural gap table, generates wiring code, sandboxes it, and promotes it on pass |
| **SelfAwareLoop** | Continuous health monitor — detects memory pressure, GC anomalies, graph inconsistencies, missing files; heals autonomously |
| **KnowledgeTank** | Vector store + graph knowledge base; ingests new code as it is written |
| **DecisionGovernor** | Policy engine that approves or blocks actions based on configurable rules |
| **Sandbox** | Isolated subprocess execution with timeout and resource limits — all generated code runs here first |
| **ACS_SYSTEM** | Post-quantum cryptography pipeline: CRYSTALS-Kyber key exchange, Dilithium signing, adaptive cipher selection based on CPU load |

---

## Installation

```bash
git clone <repo-url> GhostGoat
cd GhostGoat
./setup.sh        # or: make install
```

One script. No steps to remember. It chains through everything:

1. **System packages** — apt/brew (Python 3, Node, build tools)
2. **Python venv** — isolated environment in `./venv`
3. **Python packages** — core deps, then optional ML/embedding packages
4. **Editable install** — `import ghostgoat` works from anywhere in the project
5. **Dashboard** — `npm install` (skipped if Node not found)
6. **Rust backend** — `cargo build --release` (skipped if Rust not found)
7. **.env template** — created on first run; edit to add your API keys

---

## Running

After install, no venv activation needed — `make` handles it automatically.

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

`setup.sh` creates `.env` on first run. Edit it to add your keys:

```bash
# LLM — at least one key required (or leave blank to use mock)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

LLM_PROVIDER=anthropic          # anthropic | openai | gemini | mock
MEMORY_BACKEND=chromadb         # memory | chromadb | knowledge_tank
REDIS_URL=redis://localhost:6379
CHROMADB_PATH=./data/chromadb
```

> **No API key?** Set `LLM_PROVIDER=mock` — the system runs fully with a local mock LLM.

---

## Key Design Principles

**Self-assembling** — `BuildLoop` scans `SYSTEM_MAP.md` for architectural gaps, generates the bridging code using the LLM, runs it in the sandbox, and only writes it to disk if the tests pass. Gaps close themselves.

**Self-healing** — `SelfAwareLoop` runs a background monitor that detects anomalies (memory leaks, GC pressure, unhealthy knowledge graphs, missing required files) and applies targeted remediations without restarting the process. The check interval adapts: it tightens under stress and relaxes when the system is healthy.

**Zero-trust crypto** — every inter-component call that crosses a trust boundary is encrypted. The ACS pipeline selects between AES-GCM and ChaCha20-Poly1305 based on real-time CPU load. All audit log entries are signed with Ed25519. Post-quantum key exchange (CRYSTALS-Kyber) is available for forward-secrecy requirements.

**Graceful degradation** — every optional subsystem (ChromaDB, Redis, sentence-transformers, Neo4j) fails softly. The system starts and runs with zero external services using in-memory fallbacks.

**Policy-governed** — `DecisionGovernor` sits between the orchestrator and external systems. No outbound call, code execution, or resource mutation happens without passing the policy layer.

---

## Project Structure

```
GhostGoat/
├── main.py                    # Entry point
├── setup.sh                   # Installer
├── Makefile                   # make install / run / test / start
├── .env                       # Runtime config (created by setup.sh)
│
├── api/server.py              # FastAPI backend  →  :8420
├── dashboard/                 # React + Vite frontend  →  :3000
│
├── core/
│   ├── build_loop.py          # Self-assembly engine
│   ├── self_aware_loop.py     # Self-healing monitor
│   ├── sandbox.py             # Isolated code execution
│   ├── orchestrator/          # LLM orchestrator + routing
│   ├── memory/                # Memory backends
│   ├── agents/                # Agent pool + cognitive engine
│   ├── reasoning/             # Brain + knowledge graph
│   ├── diagnostics/           # Health checks
│   └── governance/            # Policy engine
│
├── ACS_SYSTEM/
│   ├── adap_pipeline/         # Adaptive encryption (crypto.py, policy.py)
│   ├── crystal_crypto/        # CRYSTALS-Kyber + Dilithium
│   ├── cipherdsl/             # Cipher chain DSL
│   └── core/                  # Metrics collector, anomaly detector, ASI engine
│
├── agents/                    # Domain agent definitions
├── frameworks/                # LLM adapters, monitoring, API gateway
├── integrations/              # External service connectors
├── security/                  # Security tools (MISP, STIX, scanning)
├── tools/                     # Tool registry and utilities
├── backend/                   # Rust scanner (optional)
└── tests/                     # pytest suite
```

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | Required |
| Node.js | 18+ | Dashboard only |
| Rust / cargo | stable | Backend scanner — optional |
| Docker | 20+ | Production stack — optional |
| API key | — | Anthropic or OpenAI; `mock` works without one |

