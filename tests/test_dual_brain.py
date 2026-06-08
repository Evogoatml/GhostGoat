import sys
import os
sys.path.insert(0, os.path.abspath("."))

from core.brain.ghostgoat_dual_brain import GhostGoatDualBrain

if __name__ == "__main__":
    brain = GhostGoatDualBrain(input_size=4)
    sample = {"features": [5.1, 3.5, 1.4, 0.2]}
    result = brain.think(sample)
    print("✅ SUCCESS!")
    print(result)
    brain.self_improve()
