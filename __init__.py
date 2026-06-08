"""
GhostGoat - Universal NLM Orchestrator
Multi-agent AI system with unified LLM, memory, and monitoring.
"""

import os
import sys

# Add subdirectories to Python path so cross-module imports work
# (e.g., multi_llm.py can `from unified_config import ...`)
_root = os.path.dirname(os.path.abspath(__file__))
for subdir in ["config", "frameworks/llm", "frameworks/monitoring", "frameworks/api"]:
    path = os.path.join(_root, subdir)
    if path not in sys.path and os.path.isdir(path):
        sys.path.insert(0, path)
