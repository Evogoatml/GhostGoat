# cogno/nodes/quantum_node.py

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4

@dataclass
class QuantumNode:
    node_id: str = field(default_factory=lambda: str(uuid4())[:8])
    
    # --- Atomic Layer (quantum properties) ---
    # Superposition: multiple possible states with amplitudes
    state_amplitudes: dict[str, float] = field(default_factory=dict)
    collapsed_state: Optional[str] = None   # None = still in superposition
    entangled_with: list[str] = field(default_factory=list)  # node IDs
    
    # --- Neural Layer (activation properties) ---
    activation: float = 0.0
    threshold: float = 0.5
    weights: dict[str, float] = field(default_factory=dict)  # {source_node_id: weight}
    bias: float = 0.0
    fired: bool = False

    def superpose(self, states: dict[str, float]):
        """Load multiple possible states with probability amplitudes."""
        total = sum(abs(v)**2 for v in states.values())
        # Normalize so |amplitudes|^2 sum to 1
        self.state_amplitudes = {k: v / (total**0.5) for k, v in states.items()}
        self.collapsed_state = None

    def observe(self) -> str:
        """Wave function collapse — probabilistic state selection."""
        if self.collapsed_state:
            return self.collapsed_state
        states = list(self.state_amplitudes.keys())
        probs = [abs(v)**2 for v in self.state_amplitudes.values()]
        self.collapsed_state = np.random.choice(states, p=probs)
        return self.collapsed_state

    def receive_signal(self, source_id: str, signal: float):
        """Synaptic input — weighted accumulation."""
        w = self.weights.get(source_id, 1.0)
        self.activation += w * signal

    def activate(self) -> Optional[float]:
        """Fire if activation crosses threshold (action potential)."""
        output = self._sigmoid(self.activation + self.bias)
        self.fired = output >= self.threshold
        return output if self.fired else None

    def strengthen_synapse(self, source_id: str, delta: float = 0.01):
        """Hebbian plasticity — fire together, wire together."""
        self.weights[source_id] = self.weights.get(source_id, 1.0) + delta

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + np.exp(-x))

    def reset(self):
        self.activation = 0.0
        self.fired = False
        self.collapsed_state = None