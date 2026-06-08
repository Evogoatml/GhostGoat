#!/usr/bin/env python3
"""
Dual-Brain Integration Bridge — fixed imports
"""
import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                '..', 'agent_byte-master', 'brain'))

try:
    from ghostgoat_dual_brain import GhostGoatDualBrain
    DUAL_BRAIN_AVAILABLE = True
except ImportError as e:
    logging.warning(f"dual_brain not available: {e}")
    GhostGoatDualBrain = None
    DUAL_BRAIN_AVAILABLE = False

logger = logging.getLogger(__name__)
_dual_brain = None

def get_dual_brain(input_size: int = 128):
    global _dual_brain
    if _dual_brain is None:
        if not DUAL_BRAIN_AVAILABLE:
            logger.warning("dual_brain unavailable — returning None")
            return None
        _dual_brain = GhostGoatDualBrain(input_size=input_size)
        logger.info("dual_brain initialized")
    return _dual_brain

def auto_wire_dual_brain(orchestrator):
    brain = get_dual_brain()
    if brain is None:
        return
    original_think = getattr(orchestrator, 'think', None)
    def new_think(input_data):
        neural_result = brain.think(input_data)
        if original_think:
            try:
                original_result = original_think(input_data)
                return {**original_result, **neural_result,
                        "used_dual_brain": True}
            except Exception:
                pass
        return neural_result
    orchestrator.think = new_think
    logger.info("dual_brain wired into orchestrator")
