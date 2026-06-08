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

    def evolve_architecture(self, proposal: Dict) -> bool:
        new_hidden = proposal.get("hidden_sizes", self.hidden_sizes)
        new_act = proposal.get("activation", "relu")
        self.__init__(self.input_size, new_hidden, self.output_size, 
                     activation=new_act, dropout=proposal.get("dropout", 0.15))
        return True
