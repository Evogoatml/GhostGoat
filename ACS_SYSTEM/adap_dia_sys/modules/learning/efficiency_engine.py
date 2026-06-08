from typing import Any, Dict, List


class EfficiencyEngine:
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}

    def record(self, metric: str, value: float):
        if metric not in self.metrics:
            self.metrics[metric] = []
        self.metrics[metric].append(value)

    def get_efficiency(self, metric: str) -> float:
        vals = self.metrics.get(metric, [])
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    def suggest_optimizations(self) -> List[str]:
        suggestions = []
        for metric, vals in self.metrics.items():
            avg = sum(vals) / len(vals)
            if avg > 80:
                suggestions.append(f"High {metric}: consider scaling {metric}")
        return suggestions