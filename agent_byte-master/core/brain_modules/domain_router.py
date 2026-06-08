"""DomainRouter — routes user queries to domain-specific workflow subgraphs."""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PROJECTS_DIR = Path(
    "/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows/projects"
)

DOMAIN_KEYWORDS = {
    "natural_language_processing": [
        "nlp",
        "tokeniz",
        "embed",
        "bert",
        "gpt",
        "transformer",
        "text",
        "sentiment",
        "lang",
    ],
    "computer_vision": [
        "cv",
        "image",
        "cnn",
        "resnet",
        "yolo",
        "opencv",
        "pixel",
        "convolution",
        "vision",
    ],
    "security": [
        "security",
        "pentest",
        "vulnerability",
        "exploit",
        "scan",
        "firewall",
        "auth",
        "jwt",
        "session",
    ],
    "cryptography": [
        "crypto",
        "aes",
        "rsa",
        "cipher",
        "encrypt",
        "decrypt",
        "hash",
        "steganography",
        "diffie",
    ],
    "machine_learning": [
        "ml",
        "sklearn",
        "kmeans",
        "cluster",
        "regression",
        "classifier",
        "svm",
        "decision tree",
    ],
    "deep_learning": [
        "deep",
        "neural",
        "tensorflow",
        "pytorch",
        "keras",
        "backprop",
        "gradient",
        "epoch",
    ],
    "reinforcement_learning": [
        "rl",
        "q-learning",
        "policy",
        "agent",
        "reward",
        "environment",
        "markov",
    ],
    "web_development": [
        "web",
        "flask",
        "django",
        "fastapi",
        "html",
        "css",
        "rest",
        "api",
        "endpoint",
    ],
    "data_engineering": [
        "etl",
        "pipeline",
        "spark",
        "kafka",
        "sql",
        "database",
        "pandas",
        "csv",
        "json",
    ],
    "devops": [
        "docker",
        "kubernetes",
        "k8s",
        "ci/cd",
        "deploy",
        "lambda",
        "terraform",
        "ansible",
    ],
}


class DomainRouter:
    def __init__(self, projects_dir=None):
        self.projects_dir = projects_dir or PROJECTS_DIR
        self._domains = defaultdict(list)
        self._domain_stats = {}
        self._build_index()

    def _build_index(self):
        for f in self.projects_dir.glob("*.workflow.json"):
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            wid = wf.get("workflow_id", f.stem)
            ptype = wf.get("project_type", "unknown")
            name = wf.get("project_name", "")
            if ptype != "unknown":
                self._domains[ptype].append(wid)
            for d in self._detect_domain(name):
                if wid not in self._domains[d]:
                    self._domains[d].append(wid)
        for d, wids in self._domains.items():
            self._domain_stats[d] = {"workflow_count": len(wids), "sample_ids": wids[:5]}

    def classify(self, query):
        q = query.lower()
        scores = {}
        for domain, kws in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in kws if kw in q)
            if score > 0:
                scores[domain] = score
        return max(scores, key=scores.get) if scores else "general"

    def classify_multi(self, query, top_k=3):
        q = query.lower()
        scores = {}
        for domain, kws in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in kws if kw in q)
            if score > 0:
                scores[domain] = score
        return [
            d
            for d, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        ]

    def get_expert_graph(self, domain):
        wids = self._domains.get(domain, [])
        workflows = []
        for wid in wids:
            f = self.projects_dir / f"{wid}.workflow.json"
            if f.exists():
                workflows.append(json.loads(f.read_text(encoding="utf-8")))
        return {
            "domain": domain,
            "workflow_count": len(workflows),
            "workflows": workflows,
        }

    def get_workflow_domains(self, workflow_id):
        return [d for d, wids in self._domains.items() if workflow_id in wids]

    def list_domains(self):
        return sorted(self._domains.keys())

    def get_domain_stats(self, domain=None):
        if domain:
            return self._domain_stats.get(domain, {"workflow_count": 0})
        return dict(self._domain_stats)

    def get_coverage_report(self):
        total = sum(len(v) for v in self._domains.values())
        return {
            "total_workflows": len(list(self.projects_dir.glob("*.workflow.json"))),
            "indexed_workflows": total,
            "domains": len(self._domains),
            "coverage": {
                d: {
                    "count": len(wids),
                    "percentage": len(wids) / max(total, 1) * 100,
                }
                for d, wids in sorted(
                    self._domains.items(), key=lambda x: -len(x[1])
                )
            },
        }

    @staticmethod
    def _detect_domain(text):
        t = text.lower()
        found = set()
        for domain, kws in DOMAIN_KEYWORDS.items():
            if any(kw in t for kw in kws):
                found.add(domain)
        return found
