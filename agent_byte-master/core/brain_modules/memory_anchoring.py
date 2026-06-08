"""MemoryAnchoring — stores (query, workflow, outcome) triples for better retrieval."""
from __future__ import annotations
import json, time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MEM_STORAGE = Path.home() / ".ghostgoat" / "brain" / "memory_anchors.json"


class Anchor:
    def __init__(self, query, workflow_id, outcome, timestamp=None, metadata=None):
        self.query = query
        self.workflow_id = workflow_id
        self.outcome = outcome
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "query": self.query,
            "workflow_id": self.workflow_id,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            d["query"],
            d["workflow_id"],
            d["outcome"],
            d.get("timestamp"),
            d.get("metadata", {}),
        )


class MemoryAnchoring:
    def __init__(self, storage_path=None):
        self.storage_path = Path(storage_path) if storage_path else MEM_STORAGE
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._anchors = []
        self._wf_scores = defaultdict(float)
        self._load()

    def anchor(self, query, workflow_id, success, metadata=None):
        self._anchors.append(Anchor(query, workflow_id, success, metadata=metadata))
        self._wf_scores[workflow_id] += 1.0 if success else -0.5
        self._persist()

    def boost(self, query, candidates):
        scored = []
        for cand in candidates:
            wid = cand.get("workflow_id") or cand.get("id")
            base = cand.get("similarity", cand.get("score", 0.5))
            mem_bonus = self._wf_scores.get(wid, 0.0) * 0.1
            query_bonus = self._query_similarity_boost(query, wid)
            scored.append(
                {
                    **cand,
                    "boosted_score": base + mem_bonus + query_bonus,
                    "memory_bonus": mem_bonus,
                    "query_bonus": query_bonus,
                }
            )
        scored.sort(key=lambda x: x["boosted_score"], reverse=True)
        return scored

    def best_for_query(self, query, top_k=3):
        bonus = defaultdict(float)
        for a in self._anchors:
            sim = self._text_similarity(query, a.query)
            if sim > 0.6:
                bonus[a.workflow_id] += sim * (1.0 if a.outcome else -0.3)
        return sorted(bonus.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def get_workflow_stats(self, workflow_id):
        anchors = [a for a in self._anchors if a.workflow_id == workflow_id]
        if not anchors:
            return {"uses": 0, "success_rate": None, "avg_score": 0.0}
        successes = sum(1 for a in anchors if a.outcome)
        return {
            "uses": len(anchors),
            "success_rate": successes / len(anchors),
            "avg_score": self._wf_scores[workflow_id] / len(anchors),
            "last_used": max(a.timestamp for a in anchors),
        }

    def get_global_stats(self):
        if not self._anchors:
            return {"anchors": 0, "unique_workflows": 0, "overall_success_rate": 0}
        successes = sum(1 for a in self._anchors if a.outcome)
        return {
            "anchors": len(self._anchors),
            "unique_workflows": len(self._wf_scores),
            "overall_success_rate": successes / len(self._anchors),
            "top_workflows": sorted(
                self._wf_scores.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def _persist(self):
        data = {
            "anchors": [a.to_dict() for a in self._anchors],
            "scores": dict(self._wf_scores),
        }
        tmp = self.storage_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.storage_path)

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            d = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self._anchors = [Anchor.from_dict(x) for x in d.get("anchors", [])]
            self._wf_scores = defaultdict(float, d.get("scores", {}))
        except Exception:
            pass

    @staticmethod
    def _text_similarity(a, b):
        ta = set(a.lower().split())
        tb = set(b.lower().split())
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)

    def _query_similarity_boost(self, query, workflow_id):
        bonus = 0.0
        for a in self._anchors:
            if a.workflow_id != workflow_id:
                continue
            sim = self._text_similarity(query, a.query)
            if sim > 0.5:
                bonus += sim * (0.5 if a.outcome else -0.2)
        return min(bonus, 1.0)
