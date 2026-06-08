#!/usr/bin/env python3
# modules/learning/neural_core.py
import os, json, math, time, random

BRAIN_PATH = os.path.expanduser("~/adaptive_vault/data/brain_core.json")

class NeuralCore:
    """Vault's evolving cognitive model."""
    def __init__(self):
        self.brain = self._load()
        self.session = {"events": [], "start": time.time()}
        print("[BRAIN] Neural core loaded.")

    def _load(self):
        if not os.path.exists(BRAIN_PATH):
            return {
                "modules": {},
                "concepts": {"stability": 0.5, "efficiency": 0.5, "awareness": 0.5},
                "links": {},
                "evolution": 0
            }
        with open(BRAIN_PATH, "r") as f:
            return json.load(f)

    def _save(self):
        os.makedirs(os.path.dirname(BRAIN_PATH), exist_ok=True)
        with open(BRAIN_PATH, "w") as f:
            json.dump(self.brain, f, indent=2)

    def record_experience(self, module, result="success", latency=None):
        """Add experience and grow synaptic links."""
        m = self.brain["modules"].get(module, {"success": 0, "failure": 0, "avg_latency": None})
        if result == "success": m["success"] += 1
        else: m["failure"] += 1
        if latency:
            m["avg_latency"] = latency if not m["avg_latency"] else (m["avg_latency"]*0.7 + latency*0.3)
        self.brain["modules"][module] = m
        self.session["events"].append((module, result))
        self._form_links(module, result)
        self._evolve_concepts()
        self._save()

    def _form_links(self, module, result):
        """Build connections between co-active modules."""
        if len(self.session["events"]) < 2:
            return
        prev = self.session["events"][-2][0]
        self.brain["links"].setdefault(prev, {}).setdefault(module, 0)
        delta = 0.1 if result == "success" else -0.05
        self.brain["links"][prev][module] = round(
            max(0, min(1, self.brain["links"][prev][module] + delta)), 3
        )

    def _evolve_concepts(self):
        """Adjust abstract concepts like stability/efficiency/awareness."""
        total = sum(m["success"] + m["failure"] for m in self.brain["modules"].values()) or 1
        success = sum(m["success"] for m in self.brain["modules"].values())
        stability = success / total
        efficiency = random.uniform(0.8, 1.2) * stability
        awareness = math.log1p(total) / 10
        self.brain["concepts"].update({
            "stability": round(stability, 3),
            "efficiency": round(efficiency, 3),
            "awareness": round(awareness, 3)
        })
        self.brain["evolution"] += 1

    def introspect(self):
        print("\n🧠 Neural Core Status:")
        print(json.dumps(self.brain["concepts"], indent=2))
        print("Connections:", len(self.brain["links"]))
