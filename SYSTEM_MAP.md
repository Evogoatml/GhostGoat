# GhostGoat — Full System Map

**Total files**: ~3,275 (2,103 Python + JSON, JSX, TS, etc.)
**Approximate lines of code**: 40,000+
**Last updated**: 2026-03-05

---

## What This System Is

GhostGoat is a self-learning, multi-agent AI orchestration system. It takes tasks, breaks them down using an LLM, routes subtasks to specialised agents, executes them, learns from the results, and gets smarter over time. It has a cryptographic security layer (ACS_SYSTEM), a React dashboard, a Telegram interface, and a growing self-building knowledge base.

---

## Directory Overview

```
GhostGoat/
├── ACS_SYSTEM/          Cryptography, adaptive ciphers, self-evolving ASI
├── api/                 FastAPI backend (port 8420)
├── config/              Unified configuration system
│   ├── unified_config.py  Main configuration with all settings
│   └── brain_config.py    Brain-specific configuration
├── core/                Brain, orchestrator, agents, memory, learning
│   ├── intelligence/     Intelligence system (ability mgmt, knowledge frames, pattern recognition)
│   │   ├── __init__.py
│   │   ├── ability_manager.py      Ability template management
│   │   ├── knowledge_frame_manager.py  Knowledge frame storage & retrieval
│   │   ├── pattern_recognizer.py    Pattern recognition system
│   │   ├── analogical_transferer.py Cross-domain ability transfer
│   │   └── self_directed_learner.py Self-improvement learning system
│   ├── orchestrator/     Central coordination layer
│   ├── reasoning/        Brain + knowledge graph
│   ├── agents/           Agent pool + cognitive engine
│   ├── memory/           Memory backends
│   ├── governance/       Policy engine
│   ├── diagnostics/      Health checks
│   └── learning/         Learning & self-improvement
├── dashboard/           React/Vite frontend (port 3000)
├── data/                Seed knowledge, vector DB, logs
├── docs/                Architecture documentation
├── examples/            Unified demo
├── frameworks/          LLM adapters, agent framework adapters
├── integrations/        Telegram, Google, HuggingFace, tunnels
├── tests/               11 test files
└── tools/               Tool registry
```

---

## 1. ACS_SYSTEM — Cryptography & Adaptive Intelligence

### adap_pipeline/ — Adaptive Cryptographic Pipeline
| File | What it does |
|------|-------------|
| `main.py` | Module auto-loader — drops any `.py` in `/modules` and it loads automatically |
| `app.py` | Pipeline orchestration entry point |
| `adaptive_vault.py` | Live console for adaptive encryption selection |
| `crypto.py` | Encryption and signing operations |
| `policy.py` | Cipher selection policies |
| `translator_gate.py` | Protocol translation gateway |
| `core_controller.py` | `ModuleWrapper` + `AdaptiveVault` — safe dynamic module loading/calling |
| `modules/api_keys.py` | Loads API keys from `~/adaptive_vault/.env` |
| `modules/api_registry.py` | Fetches and caches public API catalogue |
| `modules/network_tunnel.py` | ngrok tunnel management (activate/deactivate on demand) |
| `modules/public_api_connector.py` | External API connection with key auth + cache fallback |

> **Tool system**: `ModuleWrapper.call(func, *args)` gives GhostGoat safe, dynamic access to any module. Drop a `.py` in `/modules` → it becomes a usable tool.

### adap_dia_sys/ — Adaptive Diagnostics System
Same module structure as adap_pipeline, specialised for diagnostics, self-checks, and hash integrity.

### crystal_crypto/ — Post-Quantum Cryptography
| File | What it does |
|------|-------------|
| `crystal_system.py` | Full CRYSTALS suite orchestration |
| `crystal_lattice.py` | Lattice-based math (NTT polynomial multiplication) |
| `crypto_core.py` | Core cryptographic operations |
| `classical_ciphers.py` | AES, ChaCha20, classical algorithms |
| `homomorphic_engine.py` | Homomorphic encryption |
| `advanced_ciphers.py` | Crystal-Kyber KEM — NIST security levels 1/3/5 |

### cipherdsl/ — Cipher Chain Domain-Specific Language
Lets you define encryption pipelines in a DSL and compiles them to Python, Go, or Rust code.
- `dsl.py` — language definitions
- `engine.py` — execution engine
- `cipher_codegen.py` — code generation
- `out/go/`, `out/rust/` — generated output targets

### asi/ — Self-Evolving Agent
| File | What it does |
|------|-------------|
| `self_evolving_agent.py` | GraphRAG-based self-improving agent |
| `neuroforge_v1.py` | Neural intelligence framework |
| `self_modifying_examples.py` | Patterns for safe self-modification |
| `training_bridge.py` | Bridge to GhostGoat training data |
| `evoagent/` | EvoAgent framework: agent, memory, tools, configs |

### core/ — ACS Core
`asi_core.py`, `asi_engine.py`, `self_modifier.py`, `anomaly_detector.py`, `metrics_collector.py`

---

## 2. core/ — The Brain

### orchestrator/
The central coordination layer. Takes a user query and runs it end-to-end.

**llm_orchestrator.py** (main orchestrator, 800+ lines)
```
orchestrate(query)
  ├── _understand_query()         LLM analyses intent, domain, complexity
  ├── _fetch_training_context()   Pull relevant training knowledge → inject into LLM prompt
  ├── _decompose_task()           LLM breaks query into subtasks
  ├── _find_algorithms()          Search KnowledgeTank for relevant algorithms
  ├── _select_agents()            LLM picks best agent per task
  ├── _execute_coordinated()      Run tasks respecting dependencies
  │    └── _execute_task()        Per-task: check skill cache → run → record
  ├── _synthesize_results()       LLM produces final answer with training context
  └── _update_learning()          → SelfBuilder.learn_from_execution() → persist
```
orchestrate(query)
  ├── _understand_query()         LLM analyses intent, domain, complexity
  ├── _fetch_training_context()   Pull relevant training knowledge → inject into LLM prompt
  ├── _decompose_task()           LLM breaks query into subtasks
  ├── _find_algorithms()          Search KnowledgeTank for relevant algorithms
  ├── _select_agents()            LLM picks best agent per task
  ├── _execute_coordinated()      Run tasks respecting dependencies
  │    └── _execute_task()        Per-task: check skill cache → run → record
  ├── _synthesize_results()       LLM produces final answer with training context
  └── _update_learning()          → SelfBuilder.learn_from_execution() → persist
```

**Public methods you can call:**
- `orchestrate(query)` — give it a task, get a result
- `ingest(path)` — give it any file, it indexes itself into knowledge

**llm_powered_orchestrator.py** — extended variant with full system integration (SmartMoE, RAG, all subsystems)

**Agent capabilities recognised:**
`cryptography`, `machine_learning`, `graph_analysis`, `data_structures`, `mathematics`, `networking`, `general`

---

### reasoning/brain/

#### Brain Core
| File | What it does |
|------|-------------|
| `core.py` | Brain initialisation and component wiring |
| `reasoning_core.py` | Core reasoning engine |
| `react_engine.py` | ReAct (reason + act) loop |
| `advanced_capabilities.py` | Extended reasoning |
| ✅ `interpreter.py` | Command interpretation (currently basic regex — upgrade candidate) |
| `autonode_engine.py` | Auto-node execution pattern |

#### knowledge/
| File | What it does |
|------|-------------|
| `knowledge_tank.py` (26KB) | Indexes ~1,380 algorithm files + JSON training entries into SQLite with FTS5 |
| `self_builder.py` | Self-upgrade system: `ingest_file(path)` + `learn_from_execution()` |
| `vector_store.py` | Vector storage interface |
| `training/` | Structured JSON domain knowledge — loaded at boot, searched at query time |
| `algorithms/` | 1,380 algorithm files across 20+ subdirectories |

**Training files currently in `training/`:**
- `algorithms_reference.json` — 22+ algorithm entries (binary search, Dijkstra, BFS, etc.)
- `data_structures_guide.json` — data structure reference
- `problem_solving_patterns.json` — problem-solving frameworks
- `reasoning_frameworks.json` — reasoning patterns
- `self_learned.json` — auto-generated; grows as the bot completes tasks *(created automatically)*

**Algorithm library categories:**
sorting, searching, graphs, data structures, cryptography, ML, image processing, financial, physics, patterns, linked lists, networking, automation, utilities

#### memory/
| File | What it does |
|------|-------------|
| `unified_memory.py` | Common memory interface across backends |
| `semantic_tank.py` | Semantic knowledge storage and search |
| `embedding_memory.py` | Embedding-based retrieval |
| `context_memory.py` | Per-session context tracking |

**Supported backends:** ChromaDB, KnowledgeTank, SQLite, in-memory

#### rag/
| Component | What it does |
|-----------|-------------|
| `rag_system.py` | ChromaDB + sentence-transformers semantic search, text chunking |
| `ragflow/` | RagFlow deep document retrieval integration |
| `controlflow/` | ControlFlow agent framework with 20+ example workflows |
| `agentic_rag_mcp/` | Agentic RAG with Model Context Protocol |

#### training/ (ML training resources)
- `ml_vault.py` (19KB) — ML model training vault
- `extended/` — gradient boosting, k-NN, logistic regression, neural networks, self-organising maps, XGBoost

---

### agents/

#### agent_core/
| File | What it does |
|------|-------------|
| `agent_network.py` | SSH-based agent mesh — local (8022, 8023) + configurable remote nodes |
| `cognitive_engine.py` | Cognitive reasoning per agent |
| `decision_controller.py` | Per-agent decision logic |
| `efficiency_engine.py` | Performance optimisation |
| `context_memory.py` | Agent context tracking |

#### frameworks/agent_frameworks/
508 files covering: marketing automation, security/pentesting, web scraping, business intelligence, social media, lead generation, AWS advertising stack

---

### memory/
Mirrors `reasoning/brain/memory/` at the core level. Five backends, unified interface.

### governance/
`decision_governor.py` — approval logic for sensitive actions
`recommendation_engine.py` — task recommendations
`task_handler.py` — routing and dispatch

### diagnostics/
`diagnostic_center.py` — health checks
`self_check.py` (7KB) — self-diagnostic + auto-healing
`external_services.py` — external service health
`network_context.py` — network state

### learning/
`learning_core.py` — task result recording and analysis
`neural_core.py` — neural learning engine
`user_behavior.py` — user behaviour tracking

### skills/
| File | What it does |
|------|-------------|
| `skill_library.py` (12KB) | Agent-K: caches proven task→solution pairs. LRU eviction (500 max). Confidence threshold 0.6. Stored at `~/.ghostgoat/skills/library.json` |
| `seeder.py` (7KB) | Bootstraps skill library + domain knowledge on first run |

### Core Integration Files
| File | What it does |
|------|-------------|
| `ghostgoat_core.py` (26KB) | Main standalone orchestrator with LLM caching (128 responses), semantic memory, self-evolution gates |
| `ghostgoat2.py` (11KB) | Simplified variant |
| `self_aware_loop.py` (13KB) | Continuous self-aware execution loop |
| `unified_integration.py` (13KB) | Lazy-load system integration layer |
| `core_integration.py` (800 lines) | Wires NeuroGraph, Optimizer, CognitiveEngine, Diagnostics, Memory, Governance, Learning, Agent Frameworks |
| `neurograph.py` | Graph-based reasoning |
| `optimizer.py` | Performance optimisation |
| `service_registry.py` | Service discovery |
| `web_search.py` | Web search integration |

---

## 3. frameworks/

### llm/ — LLM Adapters
| Adapter | Provider |
|---------|---------|
| `multi_llm.py` | Unified interface: OpenAI, Anthropic Claude, Google Gemini, Mock |
| `claude_adapter.py` | Anthropic Claude |
| `gemini_adapter.py` | Google Gemini |

### agents/ — Agent Framework Adapters
| Adapter | Framework |
|---------|----------|
| `crewai_adapter.py` | CrewAI |
| `swarms_adapter.py` | Swarms |
| `langgraph_adapter.py` (11KB) | LangGraph workflow graphs |
| `registry.py` | Auto-discovers which frameworks are installed |
| `executor.py` (6KB) | Task execution engine |
| `traversal.py` (5KB) | Graph traversal for agent chains |
| `vault.py` (4KB) | Agent capability vault |
| `plugin_loader.py` | Dynamic plugin loading |

---

## 4. integrations/

| File | What it does |
|------|-------------|
| `telegram_bot.py` (8KB) | Telegram interface: session management, domain routing, /memory /domains /clear /status commands |
| `google_integration.py` | Google APIs |
| `huggingface_upload.py` (8KB) | Push models/data to HuggingFace Hub |
| `network_tunnel.py` | Network tunnelling |
| `universal_api_client.py` | Universal API interface |
| `smart_moe.py` (8KB) | Mixture of Experts routing |
| `translator_gate_local.py` | Local translation gateway |

---

## 5. api/ — FastAPI Server (port 8420)

**Endpoints:**
- `/service-registry` — query registered services
- `/decision-governor` — approve/reject sensitive actions
- `/task-handler` — execute tasks
- `/efficiency-engine` — performance analysis
- `/knowledge-tank` — retrieve algorithm/training knowledge
- `/orchestrator` — LLM task planning
- `/memory` — read/write memory
- `/analytics` — system analytics
- `/health` — health check

---

## 6. dashboard/ — React/Vite UI (port 3000)

Built with React, Vite, TailwindCSS.
`App.jsx`, `HybridContext.jsx` (state), `components/`, `pages/`, `hooks/`
Connects to API server at :8420.
Launch: `npm install && npx vite --port 3000`

---

## 7. config/

`unified_config.py` — master config
- LLM: OpenAI / Anthropic / Gemini / Mock / Local
- Memory: ChromaDB / KnowledgeTank / SQLite / in-memory
- All settings override-able via env vars

`docker-compose.yml` — container orchestration
`scan.yaml` — security scan config

---

## 8. data/knowledge/ — Seed Data

| File | Content |
|------|---------|
| `agent_skills_seed.json` (25KB) | 100+ proven task→solution pairs for bootstrapping skill library |
| `domain_knowledge.json` (24KB) | Domain profiles, trigger keywords, agent definitions, tool lists for: coding, research, creative, analysis, planning |
| `orchestration_patterns.json` (20KB) | Task decomposition patterns, coordination strategies |

`vector_db/` — ChromaDB persistent storage
`logs/` — execution logs

---

## 9. tests/ (11 files)

`smoke_test.py`, `test_config.py`, `test_executor.py`, `test_governance.py`, `test_learning.py`, `test_memory.py`, `test_multi_llm.py`, `test_orchestrator.py`, `test_system.py`, `test_utils.py`

---

## What's Wired Together (Working)

| Connection | Status |
|-----------|--------|
| LLMOrchestrator → KnowledgeTank (algorithm search) | ✅ |
| LLMOrchestrator → Training knowledge → LLM context injection | ✅ |
| LLMOrchestrator → Skill Library (Agent-K cache) | ✅ |
| LLMOrchestrator → SelfBuilder (learn from every task) | ✅ |
| SelfBuilder → ingest_file (any file → knowledge) | ✅ |
| API Server → all subsystems (graceful fallback) | ✅ |
| Dashboard → API Server | ✅ |
| Telegram Bot → GhostGoat core | ✅ |
| ACS adap_pipeline module auto-loader | ✅ |
| Skill library → disk persistence | ✅ |

## What Exists but Isn't Fully Connected Yet

| Component | Gap |
|-----------|-----|
| ✅ adap_pipeline tool system → GhostGoat orchestrator | Not bridged yet |
| ✅ Sandbox trial execution | Built — `core/sandbox.py` |
| ✅ CrewAI / Swarms / LangGraph adapters | Wired into LLMOrchestrator._execute_task via registry |
| ✅ SSH agent mesh network | Defined, not fully deployed |
| ✅ Persistent agent performance metrics | Lost on restart — in-memory only |
| ✅ Self-evolving ASI (asi/) | Framework exists, not integrated into main loop |
| ✅ `interpreter.py` | Basic regex — should be LLM-driven |
| ✅ Intelligence system components | AbilityManager, KnowledgeFrameManager, PatternRecognizer, AnalogicalTransferer, SelfDirectedLearner created but need full wiring into orchestrator |
| ✅ Ability library | Initialized with 6 core abilities, needs runtime integration |
| ✅ Knowledge frames | Initialized with 8 domain frames, needs connection to RAG system |

---

## How to Run

```bash
# Full system (API + Dashboard)
python main.py

# Brain/orchestrator only
python core/ghostgoat_core.py

# Seed knowledge on first run
python -m core.skills.seeder

# ACS adaptive pipeline
python ACS_SYSTEM/adap_pipeline/main.py

# Dashboard only
cd dashboard && npm install && npx vite --port 3000
```

**Required env vars** (in `~/adaptive_vault/.env` or shell):
```
OPENAI_API_KEY or ANTHROPIC_API_KEY   ← LLM provider
APILAYER_KEY                           ← adap external APIs
NGROK_AUTHTOKEN (optional)             ← network tunnelling
```

---

## Next Build Priorities

1. **Sandbox execution layer** — trial-run tasks before real execution, promote successes to skill library
2. **adap tool bridge** — connect adap_pipeline's `ModuleWrapper` to the orchestrator so modules become callable tools
3. **Intelligence system integration** — wire ability_manager, knowledge_frame_manager, pattern_recognizer, analogical_transferer, and self_directed_learner into the main orchestrator
4. **Persistent memory of user** — remember projects, preferences, history across sessions
5. **Upgrade interpreter.py** — replace regex with LLM-driven intent parsing
6. **Wire agent frameworks** — CrewAI/LangGraph adapters into main orchestration flow

