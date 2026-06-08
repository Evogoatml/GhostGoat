#!/usr/bin/env bash
# GhostGoat full import path fixer
# Fixes ALL broken/phantom import paths across the codebase
# Safe: sed in-place only, no file moves

set -euo pipefail

ROOT="/home/popic/GhostGoat"

fix() {
    local file="$1" old="$2" new="$3"
    [ -f "$file" ] || return
    if grep -qF "$old" "$file" 2>/dev/null; then
        sed -i "s|${old}|${new}|g" "$file"
        echo "[fixed] $(basename $file): $old → $new"
    fi
}

fix_dir() {
    local dir="$1" old="$2" new="$3"
    grep -rlF "$old" "$dir" --include="*.py" 2>/dev/null | while read -r f; do
        sed -i "s|${old}|${new}|g" "$f"
        echo "[fixed] $f: $old → $new"
    done
}

echo "========================================"
echo " GhostGoat full import fixer"
echo "========================================"

# ─── 1. core.reasoning.brain.memory.* → core.memory.* ───────────────────────
echo ""
echo "--- 1. core.reasoning.brain.memory → core.memory ---"
fix_dir "$ROOT" "from core.reasoning.brain.memory.memory import" "from core.memory.memory import"
fix_dir "$ROOT" "from core.reasoning.brain.memory.embedding_memory import" "from core.memory.embedding_memory import"
fix_dir "$ROOT" "from core.reasoning.brain.memory import" "from core.memory import"

# ─── 2. core.reasoning.brain.knowledge.* → core.memory.* ────────────────────
echo ""
echo "--- 2. core.reasoning.brain.knowledge → core.memory ---"
fix_dir "$ROOT" "from core.reasoning.brain.knowledge.knowledge_tank import" "from core.memory.semantic_tank import"
fix_dir "$ROOT" "from core.reasoning.brain.knowledge.self_builder import" "from core.kernel.build_loop import"
fix_dir "$ROOT" "from core.reasoning.brain.knowledge.vector_store import" "from core.memory.vector_db import"

# ─── 3. core.reasoning.brain.* → core.brain.* ───────────────────────────────
echo ""
echo "--- 3. core.reasoning.brain.* → core.brain.* ---"
fix_dir "$ROOT" "from core.reasoning.brain.autonode_engine import" "from core.kernel.engine.autonode_engine import"
fix_dir "$ROOT" "from core.reasoning.brain.core import" "from core.brain.agent_core.core import"
fix_dir "$ROOT" "from core.reasoning.brain.optimizer import" "from core.brain.memory.optimizer import"
fix_dir "$ROOT" "from core.reasoning.brain.reasoning_core import" "from core.brain.agent_core.reasoning_core import"
fix_dir "$ROOT" "from core.reasoning.brain.interpreter import" "from core.kernel.interpreter import"
fix_dir "$ROOT" "from core.reasoning.brain.learning.neural_core import" "from core.brain.agent_core.reasoning_core import"
fix_dir "$ROOT" "from core.reasoning.brain.devtools import" "from core.diagnostics.diagnostic_center import"

# ─── 4. core.orchestrator.* → core.brain.agents.* ───────────────────────────
echo ""
echo "--- 4. core.orchestrator → core.brain.agents ---"
fix_dir "$ROOT" "from core.orchestrator.llm_orchestrator import" "from core.brain.agents.tool_agent import"
fix_dir "$ROOT" "from core.orchestrator.llm_powered_orchestrator import" "from core.brain.agents.tool_agent import"
fix_dir "$ROOT" "from core.orchestrator.meta_godel_agent import" "from core.brain.agents.meta_godel_agent import"
fix_dir "$ROOT" "from core.orchestrator.pmmago import" "from core.brain.agents.pmmago import"
fix_dir "$ROOT" "from core.orchestrator.orchestrator_integration import" "from core.brain.agents.tool_agent import"

# ─── 5. core.agents.* → core.brain.agents.* ─────────────────────────────────
echo ""
echo "--- 5. core.agents → core.brain.agents ---"
fix_dir "$ROOT" "from core.agents.specialists.agent_k import" "from core.brain.agents.specialists.agent_k import"
fix_dir "$ROOT" "from core.agents.specialists.superagi_agent import" "from core.brain.agents.specialists.superagi_agent import"
fix_dir "$ROOT" "from core.agents.specialists.agentgpt_agent import" "from core.brain.agents.specialists.agentgpt_agent import"
fix_dir "$ROOT" "from core.agents.specialists.crewai_agent import" "from core.brain.agents.specialists.crewai_agent import"
fix_dir "$ROOT" "from core.agents.specialists.swarms_agent import" "from core.brain.agents.specialists.swarms_agent import"
fix_dir "$ROOT" "from core.agents.agent_byte_integration import" "from core.brain.agents.agent_byte_integration import"
fix_dir "$ROOT" "from core.agents.agent_byte_events import" "from core.brain.adapters.agent_byte_events import"
fix_dir "$ROOT" "from core.agents.agent_byte_skill_bridge import" "from core.bridges.agent_byte_skill_bridge import"
fix_dir "$ROOT" "from core.agents.agent_core.agent_network import" "from core.brain.agent_core.agent_network import"
fix_dir "$ROOT" "from core.agents.agent_core.cognitive_engine import" "from core.kernel.engine.cognitive_engine import"
fix_dir "$ROOT" "from core.agents.agent_core.efficiency_engine import" "from core.kernel.engine.efficiency_engine import"
fix_dir "$ROOT" "from core.agents.agent_byte.core.agent import" "from vendor.agent_byte-master.core.agent import"
fix_dir "$ROOT" "from core.agents.agent_byte.core.config import" "from vendor.agent_byte-master.core.config import"
fix_dir "$ROOT" "from core.agents.agent_byte.core.interfaces import" "from vendor.agent_byte-master.core.interfaces import"
fix_dir "$ROOT" "from core.agents.agent_byte.storage.json_numpy_storage import" "from vendor.agent_byte-master.storage.json_numpy_storage import"

# ─── 6. core.frameworks.orchestrator.main.* → core.brain.agents.* ───────────
echo ""
echo "--- 6. core.frameworks → core.brain ---"
fix_dir "$ROOT" "from core.frameworks.orchestrator.main.nlm_layer import" "from core.brain.adapters.nlm_layer import"
fix_dir "$ROOT" "from core.frameworks.orchestrator.main.pmmago import" "from core.brain.agents.pmmago import"

# ─── 7. core.self_aware_loop* → core.brain.agents.self_aware_loop* ───────────
echo ""
echo "--- 7. core.self_aware_loop → core.brain.agents ---"
fix_dir "$ROOT" "from core.self_aware_loop_extensions import" "from core.brain.agents.self_aware_loop_extensions import"
fix_dir "$ROOT" "from core.self_aware_loop import" "from core.brain.agents.self_aware_loop import"

# ─── 8. core.learning.* → core.brain.agent_core.* ───────────────────────────
echo ""
echo "--- 8. core.learning → core.brain.agent_core ---"
fix_dir "$ROOT" "from core.learning.learning_core import" "from core.brain.agent_core.reasoning_core import"
fix_dir "$ROOT" "from core.learning.user_behavior import" "from core.diagnostics.diagnostic_center import"
fix_dir "$ROOT" "from core.learning.neural_plasticity import" "from core.brain.agent_core.reasoning_core import"
fix_dir "$ROOT" "from core.learning.loop_guardian import" "from core.kernel.build_loop import"
fix_dir "$ROOT" "from core.learning.neural_core import" "from core.brain.agent_core.reasoning_core import"
fix_dir "$ROOT" "from core.learning import" "from core.brain.agent_core import"

# ─── 9. core.skills.* → core.brain.agents.* ─────────────────────────────────
echo ""
echo "--- 9. core.skills → core.brain.agents ---"
fix_dir "$ROOT" "from core.skills.skill_library import" "from core.brain.agents.tool_agent import"
fix_dir "$ROOT" "from core.skills import skill_library" "from core.brain.agents import tool_agent as skill_library"
fix_dir "$ROOT" "from core.skills import" "from core.brain.agents import"

# ─── 10. core.datasets.* → data/ ─────────────────────────────────────────────
echo ""
echo "--- 10. core.datasets → core.bridges ---"
fix_dir "$ROOT" "from core.datasets.hf_bridge import" "from core.bridges.hf_bridge import"
fix_dir "$ROOT" "from core.datasets.math_seeder import" "from core.bridges.hf_bridge import"

# ─── 11. core.neurograph → core.memory.neurograph ────────────────────────────
echo ""
echo "--- 11. core.neurograph → core.memory.neurograph ---"
fix_dir "$ROOT" "from core.neurograph import" "from core.memory.neurograph import"

# ─── 12. core.distributed_agent_system → core.kernel ────────────────────────
echo ""
echo "--- 12. core.distributed_agent_system → core.kernel ---"
fix_dir "$ROOT" "from core.distributed_agent_system import" "from core.kernel.distributed_agent_system import"

# ─── 13. core.personas → core.brain.agents.personas ─────────────────────────
echo ""
echo "--- 13. core.personas → core.brain.agents.personas ---"
fix_dir "$ROOT" "from core.personas import" "from core.brain.agents.personas import"

# ─── 14. core.ghostgoat_core → flag for manual merge ────────────────────────
echo ""
echo "--- 14. core.ghostgoat_core (manual merge required) ---"
grep -rn "from core.ghostgoat_core import\|from core.ghostgoat import" "$ROOT" \
    --include="*.py" 2>/dev/null | grep -v "__pycache__" | while read -r line; do
    echo "[MANUAL] $line"
done
echo "         → after merging: from core.ghostgoat import GhostGoat, Task, RecursiveMemory"

# ─── 15. core.unified_integration → integrations/ ───────────────────────────
echo ""
echo "--- 15. core.unified_integration → integrations ---"
fix_dir "$ROOT" "from core.unified_integration import" "from integrations.unified_integration import"

# ─── 16. core.agent → core.brain.agents.base ─────────────────────────────────
echo ""
echo "--- 16. core.agent → core.brain.agents.base ---"
fix_dir "$ROOT" "from core.agent import" "from core.brain.agents.base import"

# ─── 17. ACS_SYSTEM phantom imports — flag only ──────────────────────────────
echo ""
echo "--- 17. ACS_SYSTEM phantom imports (flag only) ---"
grep -rn "from core.metrics_collector\|from core.anomaly_detector\|from core.self_modifier" \
    "$ROOT/ACS_SYSTEM" --include="*.py" 2>/dev/null | while read -r line; do
    echo "[MISSING MODULE] $line"
done
echo "         → these modules don't exist anywhere — need to be created or removed"

echo ""
echo "========================================"
echo " Done."
echo ""
echo " Verify remaining broken imports:"
echo " grep -rn 'from core\.' $ROOT --include='*.py' | grep -v '__pycache__' | grep -v 'from core\.\(brain\|kernel\|memory\|bridges\|bus\|controllers\|diagnostics\|governance\|llm\|modules\|ordinance\|pipeline\|steps\|integrations\)'"
echo "========================================"
