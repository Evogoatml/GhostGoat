"""AgentManifestLearner — parses AGENT.md content embedded in workflows."""
from __future__ import annotations
import json, re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path(
    "/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows/projects"
)


class Manifest:
    def __init__(self, workflow_id, project_name, raw):
        self.workflow_id = workflow_id
        self.project_name = project_name
        self.raw = raw
        self.parsed = self._parse(raw)

    def _parse(self, raw):
        p = {
            "agent_id": None,
            "role": None,
            "capabilities": [],
            "tools": [],
            "rules": [],
            "decisions": [],
            "self_improvement": [],
        }
        m = re.search(
            r"(?:##?\s*)?(?:Agent\s*ID|ID)\s*[:=]\s*([A-Za-z0-9_\-]+)", raw, re.I
        )
        if m:
            p["agent_id"] = m.group(1)
        m = re.search(
            r"(?:##?\s*)?(?:Role|Persona)\s*[:=]\s*(.+?)(?:\n|$)", raw, re.I
        )
        if m:
            p["role"] = m.group(1).strip()
        cap = re.search(
            r"(?:##?\s*)?(?:Capabilities|Skills|Abilities)\s*\n(.*?)(?:\n##|\n\n#|\Z)",
            raw,
            re.S | re.I,
        )
        if cap:
            for line in cap.group(1).splitlines():
                line = line.strip().lstrip("-*•").strip()
                if line and len(line) > 3:
                    p["capabilities"].append(line)
        tool = re.search(
            r"(?:##?\s*)?(?:Tools|Functions|Methods)\s*\n(.*?)(?:\n##|\n\n#|\Z)",
            raw,
            re.S | re.I,
        )
        if tool:
            for line in tool.group(1).splitlines():
                line = line.strip().lstrip("-*•").strip()
                if line and len(line) > 3:
                    p["tools"].append(line)
        rule = re.search(
            r"(?:##?\s*)?(?:Rules|Decision Tree|Logic|Behavior)\s*\n(.*?)(?:\n##|\n\n#|\Z)",
            raw,
            re.S | re.I,
        )
        if rule:
            p["rules"] = [l.strip() for l in rule.group(1).splitlines() if l.strip()]
        si = re.search(
            r"(?:##?\s*)?(?:Self[- ]?Improvement|Learning|Evolution)\s*\n(.*?)(?:\n##|\n\n#|\Z)",
            raw,
            re.S | re.I,
        )
        if si:
            p["self_improvement"] = [
                l.strip() for l in si.group(1).splitlines() if l.strip()
            ]
        return p

    def to_dict(self):
        return {
            "workflow_id": self.workflow_id,
            "project_name": self.project_name,
            **self.parsed,
        }


class AgentManifestLearner:
    def __init__(self, projects_dir=None):
        self.projects_dir = projects_dir or PROJECTS_DIR
        self._manifests = {}
        self._by_role = defaultdict(list)
        self._by_capability = defaultdict(list)

    def extract_all(self, force=False):
        if self._manifests and not force:
            return list(self._manifests.values())
        self._manifests = {}
        self._by_role = defaultdict(list)
        self._by_capability = defaultdict(list)
        for f in self.projects_dir.glob("*.workflow.json"):
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            agent = wf.get("agent") or {}
            raw = agent.get("content") or ""
            if not raw:
                for node in wf.get("nodes", []):
                    if "AGENT" in node.get("label", ""):
                        c = node.get("content", {})
                        if c.get("type") == "text":
                            raw = c.get("content", "")
                            break
            if raw and len(raw) > 50:
                m = Manifest(
                    wf.get("workflow_id", f.stem),
                    wf.get("project_name", f.stem),
                    raw,
                )
                self._manifests[m.workflow_id] = m
                if m.parsed["role"]:
                    self._by_role[m.parsed["role"]].append(m)
                for cap in m.parsed["capabilities"]:
                    self._by_capability[cap].append(m)
        return list(self._manifests.values())

    def find_role(self, q):
        q = q.lower()
        return [
            m
            for m in self._manifests.values()
            if q in (m.parsed.get("role") or "").lower()
        ]

    def find_capability(self, q):
        q = q.lower()
        return [
            m
            for m in self._manifests.values()
            if any(q in c.lower() for c in m.parsed.get("capabilities", []))
        ]

    def find_agent(self, aid):
        return next(
            (m for m in self._manifests.values() if m.parsed.get("agent_id") == aid),
            None,
        )

    def list_roles(self):
        return sorted(
            {m.parsed["role"] for m in self._manifests.values() if m.parsed["role"]}
        )

    def list_tools(self):
        return sorted(
            {t for m in self._manifests.values() for t in m.parsed.get("tools", [])}
        )

    def list_capabilities(self):
        return sorted(
            {
                c
                for m in self._manifests.values()
                for c in m.parsed.get("capabilities", [])
            }
        )

    def merge_manifests(self, role=None):
        manifests = list(self._manifests.values()) if not role else self._by_role.get(
            role, []
        )
        merged = {
            "roles": [],
            "capabilities": set(),
            "tools": set(),
            "rules": [],
            "self_improvement": [],
            "sources": [],
        }
        for m in manifests:
            merged["roles"].append(m.parsed.get("role"))
            merged["capabilities"].update(m.parsed.get("capabilities", []))
            merged["tools"].update(m.parsed.get("tools", []))
            merged["rules"].extend(m.parsed.get("rules", []))
            merged["self_improvement"].extend(m.parsed.get("self_improvement", []))
            merged["sources"].append(m.workflow_id)
        merged["roles"] = [r for r in merged["roles"] if r]
        merged["capabilities"] = sorted(merged["capabilities"])
        merged["tools"] = sorted(merged["tools"])
        return merged

    def get_stats(self):
        return {
            "total_manifests": len(self._manifests),
            "roles_found": len(self.list_roles()),
            "capabilities_found": len(self.list_capabilities()),
            "tools_found": len(self.list_tools()),
            "role_distribution": {
                role: len(manifests) for role, manifests in self._by_role.items()
            },
        }
