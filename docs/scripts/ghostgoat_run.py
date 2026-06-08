from core.ghostgoat_dual_brain import GhostGoatDualBrain

if __name__ == "__main__":
    brain = GhostGoatDualBrain(input_size=4)  # adjust to your feature count
    
    # Example usage
    sample = {"features": [5.1, 3.5, 1.4, 0.2], "metadata": {"source": "iris"}}
    result = brain.think(sample)
    print("GhostGoat thinking:", result)
    
    # Trigger self-improvement
    # brain.self_improve()   # ← will use massive training_data folder
