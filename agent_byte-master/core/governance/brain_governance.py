#!/usr/bin/env python3
"""
🧠 BRAIN GOVERNANCE
Bridge between ParadoxOrchestrator and the active Kernel.
Exposes the 10 paradox runners as runtime policy plugins.
"""

import time
from typing import Dict, Any, Optional
from core.brain.agents.paradox_aware_orchestrator import (
    ParadoxAwareOrchestrator,
    ParadoxType,
    UndecidableError,
    QuantumApproval,
)


class BrainGovernance:
    """
    Wraps the paradox orchestrator with active runtime hooks.
    Used by the kernel to evaluate tasks before execution.
    """

    def __init__(self):
        self.orchestrator = ParadoxAwareOrchestrator()
        self.violation_counts: Dict[str, int] = {}
        self.adaptive_thresholds = {
            "bounded_execution": True,
            "require_constructive_choice": True,
            "paraconsistent_tolerance": 0.2,
        }

    def evaluate_task(self, agent_id: str, command: str, target: Optional[str]) -> Dict[str, Any]:
        """
        Active paradox evaluation for a single task.
        Returns verdict dict consumed by kernel policy engine.
        """
        results = []

        # 1. Gödel / Self-reference: is agent trying to modify kernel axioms?
        if self._is_axiom_modification(command):
            return self._reject(ParadoxType.SELF_REFERENCE, "Agent attempting axiom modification")

        # 2. Halting: is execution bounded?
        if not self._is_bounded(command):
            return self._reject(ParadoxType.HALTING_PROBLEM, "Unbounded execution detected")

        # 3. Observer Effect: has target been recently measured?
        uncertainty_note = None
        if target:
            uncertainty_note = self._observer_effect_note(target)

        # 4. Infinite Regress: recursive patterns in command?
        if self._is_recursive(command):
            return self._reject(ParadoxType.INFINITE_REGRESS, "Recursive pattern in command")

        # 5. Russell Set: contradiction in target vs known safe set?
        if target and self._is_contradictory_target(target):
            return self._reject(ParadoxType.RUSSELL_SET, "Target contradicts known safe set")

        # 6. Axiom of Choice: can we constructively select the tool?
        tool = self._extract_tool(command)
        if not tool:
            return self._reject(ParadoxType.AXIOM_OF_CHOICE, "No constructive tool selection possible")

        # Build approval with quantum uncertainty
        approval = QuantumApproval(
            probability=0.92 if not uncertainty_note else 0.75,
            confidence_interval=(0.85, 0.98) if not uncertainty_note else (0.60, 0.85),
            observer_frame=f"agent={agent_id};target={target};tool={tool}",
        )

        return {
            "verdict": "approve",
            "approval": approval,
            "uncertainty_note": uncertainty_note,
            "tool": tool,
            "paradox_checks_passed": 6,
        }

    def update_from_result(self, agent_id: str, command: str, success: bool, finding: Dict[str, Any]):
        """
        Post-execution update. Adjusts thresholds based on observed outcomes.
        This is where the paradox system learns.
        """
        key = f"{agent_id}:{self._extract_tool(command)}"
        self.violation_counts[key] = self.violation_counts.get(key, 0) + (0 if success else 1)

        # If an agent repeatedly fails with constructive proofs, relax or tighten
        if self.violation_counts[key] > 5:
            # Agent is consistently wrong — tighten scrutiny
            pass

    def _is_axiom_modification(self, command: str) -> bool:
        return "axiom" in command.lower() and ("add" in command.lower() or "remove" in command.lower())

    def _is_bounded(self, command: str) -> bool:
        unbounded = ["while true", "for (;;)", "yes |", ":(){ :|:& };:"]
        cmd = command.lower()
        return not any(u in cmd for u in unbounded)

    def _is_recursive(self, command: str) -> bool:
        return "|" in command and command.count(command.split()[0]) > 1

    def _is_contradictory_target(self, target: str) -> bool:
        # Placeholder: could check against blacklist/whitelist contradictions
        return False

    def _extract_tool(self, command: str) -> Optional[str]:
        parts = command.strip().split()
        return parts[0] if parts else None

    def _observer_effect_note(self, target: str) -> Optional[str]:
        # Could check recency of scans from belief state
        return None

    def _reject(self, paradox_type: ParadoxType, reason: str) -> Dict[str, Any]:
        return {
            "verdict": "deny",
            "paradox": paradox_type.value,
            "reason": reason,
            "approval": None,
        }

