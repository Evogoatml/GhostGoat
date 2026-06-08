#!/bin/bash
set -e

cd /home/popic/GhostGoat/agent_byte-master

echo "[1/5] Ensuring all new package directories exist..."
mkdir -p core/{memory_new,checkpoint,llm_router,consensus,telemetry,stream,sandbox,optimization,multimodal,benchmark}
mkdir -p toolkit/auto_schema
mkdir -p deploy/k8s

echo "[2/5] Touching __init__.py files..."
touch core/memory_new/__init__.py
touch core/checkpoint/__init__.py
touch core/llm_router/__init__.py
touch core/consensus/__init__.py
touch core/telemetry/__init__.py
touch core/stream/__init__.py
touch core/sandbox/__init__.py
touch core/optimization/__init__.py
touch core/multimodal/__init__.py
touch core/benchmark/__init__.py
touch toolkit/auto_schema/__init__.py

echo "[3/5] Verifying all new modules compile..."
python3 -m py_compile core/embed_service.py
python3 -m py_compile core/memory_new/hierarchical_memory.py
python3 -m py_compile core/checkpoint/state_persistence.py
python3 -m py_compile core/llm_router/router.py
python3 -m py_compile core/consensus/debate_council.py
python3 -m py_compile core/telemetry/trace_exporter.py
python3 -m py_compile core/stream/sse_endpoint.py
python3 -m py_compile core/sandbox/execution_guard.py
python3 -m py_compile core/optimization/budget_cache.py
python3 -m py_compile core/multimodal/perception.py
python3 -m py_compile core/benchmark/prompt_ab.py
python3 -m py_compile toolkit/auto_schema/generator.py
echo "ALL_NEW_COMPILE_OK"

echo "[4/5] Verifying entry points..."
cd /home/popic/GhostGoat
python3 -m py_compile run_cognitive_system.py bots/orchestrator_bot.py bots/brain_bot.py api/cognitive_api.py
echo "ENTRY_POINTS_OK"

echo "[5/5] Smoke test: importing all new modules..."
python3 -c "
import sys
sys.path.insert(0, 'agent_byte-master')
from core.embed_service import embed, cosine_similarity
from core.memory_new.hierarchical_memory import TieredMemoryStore
from core.checkpoint.state_persistence import StateCheckpoint
from core.llm_router.router import LLMRouter
from core.consensus.debate_council import DebateCouncil
from core.telemetry.trace_exporter import TraceCollector
from core.sandbox.execution_guard import ExecutionGuard
from core.optimization.budget_cache import SemanticCache, CostBudget
from core.multimodal.perception import VisionAnalyzer, AudioTranscriber
from core.benchmark.prompt_ab import PromptRegistry
from toolkit.auto_schema.generator import AutoRegister
print('ALL_IMPORTS_OK')
"

echo ""
echo "=== ALL 13 UPGRADES INSTALLED AND VERIFIED ==="
echo ""
echo "Phase 1: Foundation"
echo "  embed_service.py          - Real vector embeddings (Ollama nomic-embed-text)"
echo "  hierarchical_memory.py    - Episodic / Semantic / Procedural memory with vector search"
echo "  state_persistence.py      - SQLite session checkpoints + recovery"
echo ""
echo "Phase 2: Intelligence"
echo "  auto_schema/generator.py  - Auto-register Python functions as tools with JSONSchema"
echo "  llm_router/router.py      - Cost-aware model selection (local + cloud)"
echo "  debate_council.py         - Multi-agent debate consensus (Analyst/Skeptic/Synthesizer/Arbiter)"
echo "  trace_exporter.py         - Self-documenting decision traces with Markdown export"
echo ""
echo "Phase 3: Experience & Safety"
echo "  sse_endpoint.py           - Real-time SSE streaming /v2/stream"
echo "  execution_guard.py        - Danger-pattern detection + human approval queue"
echo "  budget_cache.py           - Per-session token budget + semantic response cache"
echo ""
echo "Phase 4: Multi-Modal"
echo "  perception.py             - Vision (llava), Audio (whisper), Image generation"
echo ""
echo "Phase 5: Optimization"
echo "  prompt_ab.py              - Prompt A/B testing with auto-promotion"
echo ""
echo "Phase 6: Deployment"
echo "  deploy/docker-compose.yml - Redis + Ollama GPU + GhostGoat"
echo "  deploy/Dockerfile         - Multi-stage container build"
echo "  deploy/k8s/ghostgoat.yaml - Kubernetes 2-replica deployment"

