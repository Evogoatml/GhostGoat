"""
GhostGoat ToolMemory — Tracks which tools succeed for which tasks.
Learns from execution history to improve future tool selection.
"""
import json, time, os
from typing import Any, Dict, List
from pathlib import Path


class ToolMemory:
    """Remembers tool-task outcomes and suggests improvements."""

    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or Path.home() / ".ghostgoat" / "tool_memory.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.records: List[Dict[str, Any]] = []
        self.tool_scores: Dict[str, Dict[str, Any]] = {}  # tool_name -> {successes, failures, avg_time}
        self._load()

    def record(self, task: str, tool: str, success: bool, latency_ms: float, output_summary: str = ""):
        entry = {
            "task": task,
            "tool": tool,
            "success": success,
            "latency_ms": latency_ms,
            "output_summary": output_summary[:200],
            "timestamp": time.time(),
        }
        self.records.append(entry)
        # Update tool scores
        if tool not in self.tool_scores:
            self.tool_scores[tool] = {"successes": 0, "failures": 0, "total_ms": 0, "count": 0}
        s = self.tool_scores[tool]
        s["successes"] += 1 if success else 0
        s["failures"] += 0 if success else 1
        s["total_ms"] += latency_ms
        s["count"] += 1
        self._save()

    def get_tool_score(self, tool: str) -> Dict[str, Any]:
        s = self.tool_scores.get(tool, {"successes": 0, "failures": 0, "count": 0})
        total = s["count"]
        return {
            "tool": tool,
            "success_rate": s["successes"] / max(1, total),
            "avg_latency_ms": s["total_ms"] / max(1, total),
            "total_uses": total,
            "successes": s["successes"],
            "failures": s["failures"],
        }

    def suggest_best_tool(self, task_keywords: List[str]) -> str:
        """Suggest the tool with highest success rate matching keywords."""
        candidates = {}
        for kw in task_keywords:
            for rec in self.records:
                if kw.lower() in rec["task"].lower():
                    tool = rec["tool"]
                    if tool not in candidates:
                        candidates[tool] = []
                    candidates[tool].append(rec["success"])
        if not candidates:
            return None
        # Score by success rate
        best = max(candidates, key=lambda t: sum(candidates[t]) / max(1, len(candidates[t])))
        return best

    def get_insights(self) -> List[str]:
        """Generate human-readable insights about tool performance."""
        insights = []
        for tool, scores in sorted(self.tool_scores.items(), key=lambda x: x[1]["count"], reverse=True):
            rate = scores["successes"] / max(1, scores["count"])
            avg = scores["total_ms"] / max(1, scores["count"])
            insights.append(f"  • {tool}: {rate:.0%} success ({scores['count']} uses, {avg:.0f}ms avg)")
        return insights

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            self.records = data.get("records", [])
            self.tool_scores = data.get("tool_scores", {})
        except Exception:
            pass

    def _save(self):
        try:
            with open(self.storage_path, "w") as f:
                json.dump({"records": self.records, "tool_scores": self.tool_scores}, f, indent=2)
        except Exception:
            pass

