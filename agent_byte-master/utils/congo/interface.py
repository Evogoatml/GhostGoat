from abc import ABC, abstractmethod
from typing import Dict, Any

class Brain(ABC):
    @abstractmethod
    def think(self, input_data: Dict) -> Dict:
        """Core thinking method — replace this with Dual-Brain call"""
        pass

    @abstractmethod
    def self_improve(self):
        """Trigger autonomous training/fine-tuning"""
        pass
