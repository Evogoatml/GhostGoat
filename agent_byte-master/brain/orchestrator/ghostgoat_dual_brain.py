#!/usr/bin/env python3
"""GhostGoat Dual Brain — fixed imports"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dual_brain_neural import DualBrainNeuralNet
import numpy as np
from typing import Dict, Any

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class GhostGoatDualBrain:
    def __init__(self, input_size: int = 128,
                 hidden_sizes: list = [128, 64, 32],
                 output_size: int = 10):
        self.input_size = input_size
        self.version = "ghostgoat-dual-brain-v1"
        self.training_root = os.path.join(
            os.path.dirname(__file__), "..", "..", "core", "data")
        if TORCH_AVAILABLE:
            self.neural = DualBrainNeuralNet(
                input_size, hidden_sizes, output_size)
        else:
            self.neural = None

    def think(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not TORCH_AVAILABLE or self.neural is None:
            return {"prediction": 0, "confidence": 0.0,
                    "brain_type": "dual_brain_stub",
                    "version": self.version,
                    "metadata": input_data.get("metadata", {})}
        import torch
        features = __import__('numpy').array(
            input_data.get("features", [0.0]*self.input_size),
            dtype=__import__('numpy').float32)
        if len(features) != self.input_size:
            features = __import__('numpy').resize(features, self.input_size)
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        x = torch.tensor(features)
        neural_out = self.neural(x)
        prediction = int(torch.argmax(neural_out, dim=1).item())
        confidence = float(torch.max(torch.softmax(neural_out, dim=1)))
        return {"prediction": prediction, "confidence": confidence,
                "brain_type": "dual_brain", "version": self.version,
                "raw_output": neural_out.tolist()[0],
                "metadata": input_data.get("metadata", {})}

    def self_improve(self, samples=None):
        if samples is None:
            return {"status": "waiting_for_data",
                    "data_path": self.training_root}
        if not TORCH_AVAILABLE or self.neural is None:
            return {"status": "torch_not_available"}
        metrics = self.neural.train_on_stream(samples, epochs=5)
        return metrics
