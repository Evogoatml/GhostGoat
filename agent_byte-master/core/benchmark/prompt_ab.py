"""GhostGoat Prompt A/B Testing — Evaluate and auto-promote prompt variants."""
import json, time, logging, statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class PromptVariant:
    name: str
    template: str
    system_prompt: str = ""
    wins: int = 0
    losses: int = 0
    scores: List[float] = field(default_factory=list)
    avg_latency_ms: float = 0.0

class PromptBenchmark:
    def __init__(self, scorer: Optional[Callable[[str, str], float]] = None):
        self.scorer = scorer or self._default_scorer

    @staticmethod
    def _default_scorer(expected: str, actual: str) -> float:
        e_words = set(expected.lower().split())
        a_words = set(actual.lower().split())
        if not e_words:
            return 0.0
        overlap = len(e_words & a_words)
        return overlap / len(e_words)

    def evaluate(self, runner: Callable[[str, str], str],
                 dataset: List[Dict[str, str]],
                 variant: PromptVariant) -> Dict[str, Any]:
        scores, latencies = [], []
        for item in dataset:
            prompt = variant.template.format(**item)
            system = variant.system_prompt.format(**item) if variant.system_prompt else ""
            t0 = time.time()
            actual = runner(prompt, system)
            lat = (time.time() - t0) * 1000
            score = self.scorer(item.get("expected", ""), actual)
            scores.append(score)
            latencies.append(lat)
        variant.scores.extend(scores)
        variant.avg_latency_ms = statistics.mean(latencies) if latencies else 0.0
        return {
            "variant": variant.name,
            "samples": len(dataset),
            "mean_score": round(statistics.mean(scores), 3) if scores else 0,
            "median_score": round(statistics.median(scores), 3) if scores else 0,
            "latency_ms": round(variant.avg_latency_ms, 1),
        }

class PromptRegistry:
    def __init__(self):
        self.slots: Dict[str, List[PromptVariant]] = {}
        self.winners: Dict[str, str] = {}

    def register(self, slot: str, variant: PromptVariant):
        self.slots.setdefault(slot, []).append(variant)

    def run_ab(self, slot: str, runner: Callable[[str, str], str],
               dataset: List[Dict[str, str]], benchmark: Optional[PromptBenchmark] = None):
        bm = benchmark or PromptBenchmark()
        variants = self.slots.get(slot, [])
        if not variants:
            logger.warning("No variants for slot %s", slot)
            return {}
        results = {}
        for v in variants:
            results[v.name] = bm.evaluate(runner, dataset, v)
        winner = max(variants, key=lambda v: (statistics.mean(v.scores) if v.scores else 0, -v.avg_latency_ms))
        self.winners[slot] = winner.name
        logger.info("Prompt A/B winner for '%s': %s (score=%.3f)", slot, winner.name,
                    statistics.mean(winner.scores) if winner.scores else 0)
        return results

    def get_prompt(self, slot: str, **kwargs) -> str:
        winner_name = self.winners.get(slot)
        if winner_name:
            v = next((v for v in self.slots.get(slot, []) if v.name == winner_name), None)
            if v:
                return v.template.format(**kwargs)
        fallback = self.slots.get(slot, [PromptVariant(name="default", template="{input}")])[0]
        return fallback.template.format(**kwargs)

