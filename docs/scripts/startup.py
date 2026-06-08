#!/usr/bin/env python3
"""
GhostGoat startup — fixed imports
"""
import sys, os, logging
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

logger = logging.getLogger(__name__)

try:
    from integrations.dual_brain_integration import (
        get_dual_brain, auto_wire_dual_brain)
    INTEGRATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"integration not available: {e}")
    get_dual_brain = None
    auto_wire_dual_brain = None
    INTEGRATION_AVAILABLE = False

def initialize_ghostgoat_brain(orchestrator=None):
    if not INTEGRATION_AVAILABLE or get_dual_brain is None:
        logger.warning("brain integration unavailable — running headless")
        return None
    brain = get_dual_brain(input_size=128)
    if orchestrator and auto_wire_dual_brain:
        auto_wire_dual_brain(orchestrator)
    logger.info("GhostGoat brain active")
    return brain
