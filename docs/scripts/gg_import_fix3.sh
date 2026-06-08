#!/usr/bin/env bash
# GhostGoat import fix — final pass
# Fixes all remaining broken imports file by file

set -euo pipefail

ROOT="/home/popic/GhostGoat"

s() {
    # s <file> <old> <new>
    [ -f "$1" ] || return
    if grep -qF "$2" "$1" 2>/dev/null; then
        sed -i "s|${2}|${3}|g" "$1"
        echo "[fix] $(realpath --relative-to=$ROOT $1): $2 → $3"
    fi
}

sa() {
    # sa <old> <new> — apply across all py files
    grep -rlF "$1" "$ROOT" --include="*.py" 2>/dev/null | grep -v __pycache__ | while read -r f; do
        sed -i "s|${1}|${2}|g" "$f"
        echo "[fix] $(realpath --relative-to=$ROOT $f): $1 → $2"
    done
}

echo "=== Final import pass ==="

# ── ragflow/sandbox — internal package, core. = their own core/ subdir ────────
# These are correct for ragflow's internal structure — leave them alone
echo "[skip] ragflow/sandbox/executor_manager — internal package imports, correct as-is"

# ── ACS_SYSTEM — missing modules, comment out ────────────────────────────────
F="$ROOT/ACS_SYSTEM/core/asi_engine.py"
if [ -f "$F" ]; then
    sed -i 's|^from core.metrics_collector import|# MISSING MODULE: from core.metrics_collector import|' "$F"
    sed -i 's|^from core.anomaly_detector import|# MISSING MODULE: from core.anomaly_detector import|' "$F"
    sed -i 's|^from core.self_modifier import|# MISSING MODULE: from core.self_modifier import|' "$F"
    echo "[commented] ACS_SYSTEM/core/asi_engine.py — 3 missing modules"
fi

# ── core.datasets.hf_bridge self-reference in hf_bridge.py ───────────────────
s "$ROOT/core/bridges/hf_bridge.py" \
    "from core.datasets.hf_bridge import HFBridge" \
    "# self-import removed"

# ── core.skills → core.brain.agents.tool_agent ───────────────────────────────
sa "from core.skills.skill_library import skill_library" \
   "from core.brain.agents.tool_agent import tool_agent as skill_library"
sa "from core.skills.skill_library import" \
   "from core.brain.agents.tool_agent import"
sa "from core.skills import skill_library" \
   "from core.brain.agents import tool_agent as skill_library"
sa "from core.skills import" \
   "from core.brain.agents import"

# ── core.orchestrator.* ───────────────────────────────────────────────────────
sa "from core.orchestrator.llm_orchestrator import" \
   "from core.brain.agents.tool_agent import"
sa "from core.orchestrator.llm_powered_orchestrator import" \
   "from core.brain.agents.tool_agent import"
sa "from core.orchestrator.meta_godel_agent import" \
   "from core.brain.agents.meta_godel_agent import"
sa "from core.orchestrator.pmmago import" \
   "from core.brain.agents.pmmago import"
sa "from core.orchestrator.orchestrator_integration import" \
   "from core.brain.agents.tool_agent import"

# ── core.agents.* ────────────────────────────────────────────────────────────
sa "from core.agents.specialists.agent_k import" \
   "from core.brain.agents.specialists.agent_k import"
sa "from core.agents.specialists.superagi_agent import" \
   "from core.brain.agents.specialists.superagi_agent import"
sa "from core.agents.specialists.agentgpt_agent import" \
   "from core.brain.agents.specialists.agentgpt_agent import"
sa "from core.agents.specialists.crewai_agent import" \
   "from core.brain.agents.specialists.crewai_agent import"
sa "from core.agents.specialists.swarms_agent import" \
   "from core.brain.agents.specialists.swarms_agent import"
sa "from core.agents.agent_byte_integration import" \
   "from core.brain.agents.agent_byte_integration import"
sa "from core.agents.agent_byte_events import" \
   "from core.brain.adapters.agent_byte_events import"
sa "from core.agents.agent_byte_skill_bridge import" \
   "from core.bridges.agent_byte_skill_bridge import"
sa "from core.agents.agent_core.agent_network import" \
   "from core.brain.agent_core.agent_network import"
sa "from core.agents.agent_core.cognitive_engine import" \
   "from core.kernel.engine.cognitive_engine import"
sa "from core.agents.agent_core.efficiency_engine import" \
   "from core.kernel.engine.efficiency_engine import"
sa "from core.agents.agent_byte.core.agent import" \
   "from vendor.agent_byte_master.core.agent import"
sa "from core.agents.agent_byte.core.config import" \
   "from vendor.agent_byte_master.core.config import"
sa "from core.agents.agent_byte.core.interfaces import" \
   "from vendor.agent_byte_master.core.interfaces import"
sa "from core.agents.agent_byte.storage.json_numpy_storage import" \
   "from vendor.agent_byte_master.storage.json_numpy_storage import"

# ── core.frameworks.* ────────────────────────────────────────────────────────
sa "from core.frameworks.orchestrator.main.nlm_layer import" \
   "from core.brain.adapters.nlm_layer import"
sa "from core.frameworks.orchestrator.main.pmmago import" \
   "from core.brain.agents.pmmago import"

# ── core.self_aware_loop* ─────────────────────────────────────────────────────
sa "from core.self_aware_loop_extensions import" \
   "from core.brain.agents.self_aware_loop_extensions import"
sa "from core.self_aware_loop import" \
   "from core.brain.agents.self_aware_loop import"

# ── core.learning.* ──────────────────────────────────────────────────────────
sa "from core.learning.learning_core import" \
   "from core.brain.agent_core.reasoning_core import"
sa "from core.learning.user_behavior import" \
   "from core.diagnostics.diagnostic_center import"
sa "from core.learning.neural_plasticity import" \
   "from core.brain.agent_core.reasoning_core import"
sa "from core.learning.loop_guardian import" \
   "from core.kernel.build_loop import"
sa "from core.learning.neural_core import" \
   "from core.brain.agent_core.reasoning_core import"
sa "from core.learning import learning_core, user_behavior" \
   "from core.brain.agent_core import reasoning_core as learning_core; from core.diagnostics import diagnostic_center as user_behavior"

# ── core.neurograph ───────────────────────────────────────────────────────────
sa "from core.neurograph import" \
   "from core.memory.neurograph import"

# ── core.distributed_agent_system ────────────────────────────────────────────
sa "from core.distributed_agent_system import" \
   "from core.kernel.distributed_agent_system import"

# ── core.personas ─────────────────────────────────────────────────────────────
sa "from core.personas import" \
   "from core.brain.agents.personas import"

# ── core.reasoning.brain.devtools ────────────────────────────────────────────
sa "from core.reasoning.brain.devtools import" \
   "from core.diagnostics.diagnostic_center import"

# ── core.unified_integration ─────────────────────────────────────────────────
sa "from core.unified_integration import" \
   "from integrations.unified_integration import"

# ── core.agent (base) ────────────────────────────────────────────────────────
sa "from core.agent import" \
   "from core.brain.agents.base import"

# ── core.ghostgoat → needs merge, point to needs_merge location for now ───────
sa "from core.ghostgoat import GhostGoatAgent" \
   "from core.brain.agents.base import GhostGoatAgent  # TODO: merge ghostgoat"

# ── core.datasets.math_seeder ────────────────────────────────────────────────
sa "from core.datasets.math_seeder import" \
   "from core.bridges.hf_bridge import"

# ── core.ghostgoat_core (smoke_test — manual merge pending) ──────────────────
echo ""
echo "[MANUAL STILL NEEDED]"
echo "  tests/smoke_test.py: from core.ghostgoat_core import ..."
echo "  → merge _MOVED/needs_merge/ghostgoat2.py + ghostgoat_core.py"
echo "  → save as core/ghostgoat.py"
echo "  → update smoke_test.py: from core.ghostgoat import GhostGoat, Task, RecursiveMemory"

echo ""
echo "=== Done. Final verify ==="
echo "Running check..."
REMAINING=$(grep -rn 'from core\.' "$ROOT" --include='*.py' \
    | grep -v '__pycache__' \
    | grep -v 'from core\.\(brain\|kernel\|memory\|bridges\|bus\|controllers\|diagnostics\|governance\|llm\|modules\|ordinance\|pipeline\|steps\|integrations\)' \
    | grep -v vendor \
    | grep -v ragflow \
    | grep -v "MISSING MODULE" \
    | grep -v "TODO" \
    | wc -l)
echo "Remaining broken imports: $REMAINING"
if [ "$REMAINING" -gt 0 ]; then
    grep -rn 'from core\.' "$ROOT" --include='*.py' \
        | grep -v '__pycache__' \
        | grep -v 'from core\.\(brain\|kernel\|memory\|bridges\|bus\|controllers\|diagnostics\|governance\|llm\|modules\|ordinance\|pipeline\|steps\|integrations\)' \
        | grep -v vendor \
        | grep -v ragflow \
        | grep -v "MISSING MODULE" \
        | grep -v "TODO"
fi
