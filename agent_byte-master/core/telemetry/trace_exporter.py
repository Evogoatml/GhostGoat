"""GhostGoat Trace Exporter — Decision traces to markdown/JSON."""
import json, time, uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

@dataclass
class DecisionTrace:
    trace_id: str = field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    goal: str = ""
    mode: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    final_result: Dict[str, Any] = field(default_factory=dict)
    alternatives_considered: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    model_used: str = ""
    cost_usd_estimate: float = 0.0
    latency_ms: float = 0.0

class TraceCollector:
    def __init__(self):
        self.traces: List[DecisionTrace] = []

    def start(self, goal: str, mode: str = "unknown") -> DecisionTrace:
        t = DecisionTrace(goal=goal, mode=mode)
        self.traces.append(t)
        return t

    def add_step(self, trace: DecisionTrace, phase: str, data: Dict[str, Any]):
        trace.steps.append({"phase": phase, "timestamp": time.time(), "data": data})

    def add_error(self, trace: DecisionTrace, error: str):
        trace.errors_encountered.append(error)

    def add_alternative(self, trace: DecisionTrace, alt: str):
        trace.alternatives_considered.append(alt)

    def finalize(self, trace: DecisionTrace, result: Dict[str, Any], latency_ms: float = 0.0):
        trace.final_result = result
        trace.latency_ms = latency_ms
        trace.timestamp = time.time()

    def to_markdown(self, trace: DecisionTrace) -> str:
        md = f"# Decision Trace: {trace.trace_id}\n\n"
        md += f"**Goal:** {trace.goal}\n\n"
        md += f"**Mode:** {trace.mode}  |  **Model:** {trace.model_used}  |  **Latency:** {trace.latency_ms:.0f}ms\n\n"
        md += f"**Cost Estimate:** ${trace.cost_usd_estimate:.4f}\n\n"
        if trace.alternatives_considered:
            md += "## Alternatives Considered\n" + "\n".join(f"- {a}" for a in trace.alternatives_considered) + "\n\n"
        md += "## Steps\n\n"
        for s in trace.steps:
            md += f"### [{s['phase']}]\n```json\n{json.dumps(s['data'], indent=2, default=str)}\n```\n\n"
        if trace.errors_encountered:
            md += "## Errors\n" + "\n".join(f"- {e}" for e in trace.errors_encountered) + "\n\n"
        md += "## Final Result\n```json\n" + json.dumps(trace.final_result, indent=2, default=str) + "\n```\n"
        return md

    def export_all(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for t in self.traces:
                f.write(json.dumps(asdict(t), default=str) + "\n")

