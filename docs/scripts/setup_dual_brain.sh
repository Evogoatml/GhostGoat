#!/bin/bash

echo "=== Setting up GhostGoat Dual-Brain ==="

# Create folders
mkdir -p core/brain core/training_data/{raw,processed/{train,val,test},replay_buffer,promoted,versions,synthetic}

# 1. Neural Engine
cat > core/brain/dual_brain_neural.py << 'EOF'
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from typing import List, Dict, Tuple

class DualBrainNeuralNet(nn.Module):
    def __init__(self, input_size: int, hidden_sizes: List[int] = [128, 64, 32],
                 output_size: int = 10, activation: str = 'relu', dropout: float = 0.15):
        super().__init__()
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.output_size = output_size

        layers = []
        prev = input_size
        for h in hidden_sizes:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU() if activation == 'relu' else nn.GELU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev = h
        layers.append(nn.Linear(prev, output_size))
        self.net = nn.Sequential(*layers)

        self.optimizer = None
        self.criterion = nn.CrossEntropyLoss()
        self.history = []

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    def train_on_stream(self, samples: List[Tuple[np.ndarray, int]], 
                       batch_size: int = 64, epochs: int = 5, lr: float = 1e-3) -> Dict:
        if self.optimizer is None:
            self.optimizer = optim.AdamW(self.parameters(), lr=lr, weight_decay=1e-4)

        X = torch.tensor(np.array([s[0] for s in samples]), dtype=torch.float32)
        y = torch.tensor([s[1] for s in samples], dtype=torch.long)

        loader = DataLoader(TensorDataset(X, y), batch_size=batch_size, shuffle=True)

        for epoch in range(epochs):
            epoch_loss = 0.0
            for bx, by in loader:
                self.optimizer.zero_grad()
                outputs = self(bx)
                loss = self.criterion(outputs, by)
                loss.backward()
                self.optimizer.step()
                epoch_loss += loss.item()
            self.history.append({'epoch': epoch, 'loss': epoch_loss / len(loader)})

        return {
            "status": "improved",
            "loss": float(np.mean([h['loss'] for h in self.history[-epochs:]])),
            "architecture": self.hidden_sizes,
            "samples": len(samples)
        }
EOF

# 2. Main Dual Brain
cat > core/brain/ghostgoat_dual_brain.py << 'EOF'
from dual_brain_neural import DualBrainNeuralNet
import torch
import numpy as np
from typing import Dict, Any

class GhostGoatDualBrain:
    def __init__(self, input_size: int = 4, hidden_sizes: list = [128, 64, 32], output_size: int = 10):
        self.neural = DualBrainNeuralNet(input_size, hidden_sizes, output_size)
        self.training_root = "core/training_data"
        self.version = "ghostgoat-dual-brain-v1"

    def think(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        features = np.array(input_data.get("features", []), dtype=np.float32)
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        x = torch.tensor(features)
        neural_out = self.neural(x)
        
        prediction = int(torch.argmax(neural_out, dim=1).item())
        confidence = float(torch.max(torch.softmax(neural_out, dim=1)))

        return {
            "prediction": prediction,
            "confidence": confidence,
            "brain_type": "dual_brain",
            "version": self.version,
            "metadata": input_data.get("metadata", {})
        }

    def self_improve(self, samples=None):
        if samples is None:
            print(f"📁 Looking for data in {self.training_root}/processed/train/")
            return {"status": "waiting_for_data"}
        metrics = self.neural.train_on_stream(samples, epochs=3)
        print(f"🧠 Self-improved | Loss: {metrics['loss']:.4f}")
        return metrics
EOF

# 3. Test file with fixed path
cat > core/test_dual_brain.py << 'EOF'
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from core.brain.ghostgoat_dual_brain import GhostGoatDualBrain

if __name__ == "__main__":
    brain = GhostGoatDualBrain(input_size=4)
    sample = {"features": [5.1, 3.5, 1.4, 0.2]}
    print("✅ Test Output:", brain.think(sample))
    brain.self_improve()
EOF

chmod +x core/setup_massive_training.sh 2>/dev/null || true

echo "✅ All files created!"
echo "Now run these two commands:"
echo "python -m core.test_dual_brain"
