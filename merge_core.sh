#!/bin/bash
set -e

cd /home/popic/GhostGoat

echo "[1/7] Moving directories from root core/ into agent_byte-master/core/..."

# Directories that do NOT already exist in agent_byte-master/core/ — safe to mv
mv core/brain              agent_byte-master/core/brain
mv core/memory             agent_byte-master/core/memory
mv core/agents             agent_byte-master/core/agents
mv core/modules            agent_byte-master/core/modules
mv core/cognitive          agent_byte-master/core/cognitive
mv core/graphrag           agent_byte-master/core/graphrag
mv core/intelligence       agent_byte-master/core/intelligence
mv core/reasoning          agent_byte-master/core/reasoning
mv core/workflows          agent_byte-master/core/workflows

echo "[2/7] Removing empty placeholder dirs..."
rmdir core/diagnostics core/governance core/learning core/orchestrator core/skills core/service_registry 2>/dev/null || true

echo "[3/7] Moving top-level .py files only if they don't collide..."

[ ! -f "agent_byte-master/core/ghostgoat_core.py" ]      && mv core/ghostgoat_core.py      agent_byte-master/core/ghostgoat_core.py      || rm -f core/ghostgoat_core.py
[ ! -f "agent_byte-master/core/neurograph.py" ]          && mv core/neurograph.py          agent_byte-master/core/neurograph.py          || rm -f core/neurograph.py
[ ! -f "agent_byte-master/core/optimizer.py" ]           && mv core/optimizer.py           agent_byte-master/core/optimizer.py           || rm -f core/optimizer.py
[ ! -f "agent_byte-master/core/self_aware_loop.py" ]    && mv core/self_aware_loop.py    agent_byte-master/core/self_aware_loop.py    || rm -f core/self_aware_loop.py
[ ! -f "agent_byte-master/core/service_registry.py" ]    && mv core/service_registry.py    agent_byte-master/core/service_registry.py    || rm -f core/service_registry.py
[ ! -f "agent_byte-master/core/unified_integration.py" ] && mv core/unified_integration.py agent_byte-master/core/unified_integration.py || rm -f core/unified_integration.py
[ ! -f "agent_byte-master/core/core_integration.py" ]    && mv core/core_integration.py    agent_byte-master/core/core_integration.py    || rm -f core/core_integration.py

echo "[4/7] Removing colliding files from root core/..."
rm -f core/__init__.py
rm -f core/core.py
rm -rf core/__pycache__

echo "[5/7] Deleting leftover root core/..."
rmdir core 2>/dev/null && echo "ROOT core/ DELETED" || echo "WARNING: root core/ not empty: $(ls core/ 2>/dev/null)"

echo "[6/7] Fixing run_cognitive_system.py sys.path..."
python3 << 'PYEOF'
import re
with open('run_cognitive_system.py', 'r') as f:
    content = f.read()
if 'ABM_ROOT' not in content:
    content = content.replace(
        'sys.path.insert(0, str(ROOT))',
        'sys.path.insert(0, str(ROOT))\nABM_ROOT = str(ROOT / "agent_byte-master")\nif ABM_ROOT not in sys.path:\n    sys.path.insert(0, ABM_ROOT)'
    )
    with open('run_cognitive_system.py', 'w') as f:
        f.write(content)
    print("Patched run_cognitive_system.py")
else:
    print("run_cognitive_system.py already patched")
PYEOF

echo "[7/7] Verifying compilation..."
python3 -m py_compile run_cognitive_system.py              && echo "OK: run_cognitive_system.py"
python3 -m py_compile bots/orchestrator_bot.py              && echo "OK: bots/orchestrator_bot.py"
python3 -m py_compile bots/brain_bot.py                     && echo "OK: bots/brain_bot.py"
python3 -m py_compile api/cognitive_api.py                  && echo "OK: api/cognitive_api.py"
python3 -m py_compile agent_byte-master/core/core.py       && echo "OK: core/core.py"

echo ""
echo "=== MERGE COMPLETE ==="
echo "Root core/ eliminated. Modules integrated into agent_byte-master/core/."
