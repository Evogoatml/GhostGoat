#!/usr/bin/env bash
# GhostGoat import fixer — updates broken imports after file moves
# Safe: only does sed in-place replacements, no file moves

set -euo pipefail

ROOT="/home/popic/GhostGoat"

fix() {
    local file="$1" old="$2" new="$3"
    if grep -qF "$old" "$file" 2>/dev/null; then
        sed -i "s|${old}|${new}|g" "$file"
        echo "[fixed] $file"
        echo "        $old → $new"
    fi
}

echo "========================================"
echo " GhostGoat import fixer"
echo "========================================"

# ─── core.task_handler → core.kernel.task_handler (moved to governance) ──────
# Actually task_handler moved to core/governance/ — fix both references
for f in \
    "$ROOT/core/governance/task_handler.py" \
    "$ROOT/integrations/core_integration.py"; do
    fix "$f" "from core.task_handler import" "from core.governance.task_handler import"
done

# ─── core.service_registry → core.kernel.service_registry ────────────────────
fix "$ROOT/core/kernel/service_registry.py" \
    "from core.service_registry import" \
    "from core.kernel.service_registry import"

# ─── core.sandbox → core.kernel.sandbox ──────────────────────────────────────
fix "$ROOT/core/kernel/build_loop.py" \
    "from core.sandbox import" \
    "from core.kernel.sandbox import"

# ─── core.system → core.kernel.system ────────────────────────────────────────
fix "$ROOT/core/kernel/system.py" \
    "from core.system import" \
    "from core.kernel.system import"

fix "$ROOT/integrations/telegram_bot.py" \
    "from core.system import" \
    "from core.kernel.system import"

# ─── core.build_loop → core.kernel.build_loop ────────────────────────────────
for f in \
    "$ROOT/core/kernel/system.py" \
    "$ROOT/tests/test_build_loop.py" \
    "$ROOT/vendor/agent_byte-master/knowledge/learning/loop_guardian.py"; do
    fix "$f" "from core.build_loop import" "from core.kernel.build_loop import"
done

# ─── core.tool_agent → core.brain.agents.tool_agent ─────────────────────────
fix "$ROOT/core/kernel/system.py" \
    "from core.tool_agent import" \
    "from core.brain.agents.tool_agent import"

# ─── core.optimizer → core.brain.memory.optimizer ────────────────────────────
fix "$ROOT/integrations/core_integration.py" \
    "from core.optimizer import" \
    "from core.brain.memory.optimizer import"

# ─── core.reasoning.brain.* — these are phantom paths that never existed ──────
# agent_core/core.py has these wrong paths — fix to actual locations
fix "$ROOT/core/brain/agent_core/core.py" \
    "from core.reasoning.brain.optimizer import" \
    "from core.brain.memory.optimizer import"

fix "$ROOT/core/brain/agent_core/core.py" \
    "from core.reasoning.brain.reasoning_core import" \
    "from core.brain.agent_core.reasoning_core import"

fix "$ROOT/core/brain/agent_core/core.py" \
    "from core.reasoning.brain.interpreter import" \
    "from core.kernel.interpreter import"

fix "$ROOT/integrations/core_integration.py" \
    "from core.reasoning.brain.reasoning_core import" \
    "from core.brain.agent_core.reasoning_core import"

# ─── core.ghostgoat_core → needs_merge — point to main.py for now ────────────
# ghostgoat_core was moved to _MOVED/needs_merge — tests/smoke_test.py imports it
# Flag these for manual fix after ghostgoat2+ghostgoat_core are merged
echo ""
echo "[MANUAL] tests/smoke_test.py still imports core.ghostgoat_core"
echo "         → after merging ghostgoat2.py + ghostgoat_core.py into core/ghostgoat.py"
echo "         → update to: from core.ghostgoat import GhostGoat, Task, RecursiveMemory"

echo ""
echo "========================================"
echo " Done. Verify with:"
echo " grep -rn 'from core\.' $ROOT --include='*.py' | grep -v '__pycache__' | grep -v 'from core\.\(brain\|kernel\|memory\|bridges\|bus\|controllers\|diagnostics\|governance\|llm\|modules\|ordinance\|pipeline\|steps\)'"
echo "========================================"

