"""WorkflowSkillManager — central orchestrator for GhostGoat workflow brain."""
from __future__ import annotations
import importlib.util, json, sys, time
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENT_BYTE = Path("/home/popic/GhostGoat/agent_byte-master")
BRAIN_DIR = AGENT_BYTE / "brain/knowledge/processed/workflows"
PROJECTS_DIR = BRAIN_DIR / "projects"
MODULES_DIR = Path(__file__).parent.resolve()

def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def _compiler(): return _load_module(MODULES_DIR / "few_shot_compiler.py", "fsc").FewShotCompiler(PROJECTS_DIR)
def _executor(): return _load_module(MODULES_DIR / "code_executor.py", "cex").CodeExecutor()
def _memory(): return _load_module(MODULES_DIR / "memory_anchoring.py", "mem").MemoryAnchoring()
def _router(): return _load_module(MODULES_DIR / "domain_router.py", "rou").DomainRouter(PROJECTS_DIR)
def _manifest(): return _load_module(MODULES_DIR / "agent_manifest_learner.py", "aml").AgentManifestLearner(PROJECTS_DIR)
def _benchmark(): return _load_module(MODULES_DIR / "benchmark_suite.py", "ben").BenchmarkSuite(PROJECTS_DIR)
def _graphrag():
    mod = _load_module(AGENT_BYTE / "core/graphrag/engine.py", "grage")
    return mod.GraphRAGEngine(storage_path=str(AGENT_BYTE / "brain/knowledge/graphrag"), embedding_dim=128)

class Skill:
    def __init__(self, workflow_id, project_name, project_type, code_snippets, metadata):
        self.workflow_id = workflow_id
        self.project_name = project_name
        self.project_type = project_type
        self.code_snippets = code_snippets
        self.metadata = metadata

    def to_dict(self):
        return {
            "workflow_id": self.workflow_id,
            "project_name": self.project_name,
            "project_type": self.project_type,
            "code_snippets": len(self.code_snippets),
            "metadata": self.metadata,
        }


class WorkflowSkillManager:
    def __init__(self, projects_dir=None):
        self.projects_dir = projects_dir or PROJECTS_DIR
        self._skills = {}
        self._skill_cache_path = BRAIN_DIR / ".skill_cache.json"
        self._load_skill_cache()

    def acquire(self, workflow_id):
        if workflow_id in self._skills:
            return self._skills[workflow_id]
        f = self.projects_dir / f"{workflow_id}.workflow.json"
        if not f.exists():
            for wf_file in self.projects_dir.glob("*.workflow.json"):
                wf = json.loads(wf_file.read_text(encoding="utf-8"))
                if wf.get("project_name") == workflow_id or wf.get("workflow_id") == workflow_id:
                    f = wf_file
                    workflow_id = wf.get("workflow_id", wf_file.stem)
                    break
            if not f.exists():
                return None
        wf = json.loads(f.read_text(encoding="utf-8"))
        skill = Skill(
            workflow_id=workflow_id,
            project_name=wf.get("project_name", workflow_id),
            project_type=wf.get("project_type", "unknown"),
            code_snippets=_compiler().extract_code_cells(wf, "python"),
            metadata={"node_count": len(wf.get("nodes", [])), "source_path": wf.get("source_path", "")},
        )
        self._skills[workflow_id] = skill
        self._save_skill_cache()
        return skill

    def list_skills(self):
        return [s.to_dict() for s in self._skills.values()]

    def has_skill(self, workflow_id):
        return workflow_id in self._skills

    def forget(self, workflow_id):
        self._skills.pop(workflow_id, None)
        self._save_skill_cache()

    def few_shot(self, instruction, workflow_ids=None, project_names=None, domain=None, shots=3, chain_of_thought=False):
        # Resolve FILE node IDs to parent workflow IDs
        resolved = []
        for wid in (workflow_ids or []):
            f = self.projects_dir / f"{wid}.workflow.json"
            if f.exists():
                resolved.append(wid)
                continue
            # Fallback: search by workflow_id field inside JSON
            found = False
            for wf_file in self.projects_dir.glob("*.workflow.json"):
                try:
                    wf = json.loads(wf_file.read_text(encoding="utf-8"))
                    if wf.get("workflow_id") == wid or wf.get("project_name") == wid or wf_file.stem == wid:
                        resolved.append(wf_file.stem)
                        found = True
                        break
                except Exception:
                    pass
            if not found:
                resolved.append(wid)
        return _compiler().build_prompt(
            instruction=instruction,
            workflow_ids=resolved,
            project_names=project_names,
            domain=domain,
            shots=shots,
            chain_of_thought=chain_of_thought,
            system_message="You are GhostGoat, an expert coding agent with access to a curated workflow library.",
        )

    def few_shot_chat(self, instruction, workflow_ids=None, shots=3):
        return _compiler().build_chat_messages(
            instruction=instruction,
            workflow_ids=workflow_ids,
            shots=shots,
            system_message="You are GhostGoat, an expert coding agent.",
        )

    def execute(self, workflow_id, cell=0):
        skill = self.acquire(workflow_id)
        if not skill:
            return {"error": f"Skill '{workflow_id}' not found", "success": False}
        if cell >= len(skill.code_snippets):
            return {"error": f"Cell {cell} out of range", "success": False}
        return _executor().run_python(skill.code_snippets[cell]["code"]).to_dict()

    def validate(self, workflow_id):
        f = self.projects_dir / f"{workflow_id}.workflow.json"
        if not f.exists():
            return {"error": "Workflow not found", "success": False}
        return _executor().validate_workflow(json.loads(f.read_text(encoding="utf-8")))

    def search(self, query, top_k=5, use_memory=True):
        """Keyword-based search (fallback) — GraphRAG hash embeddings are not semantic."""
        candidates = self._fallback_search(query, limit=top_k * 2)
        if use_memory:
            candidates = _memory().boost(query, candidates)
        return candidates[:top_k]

    def route(self, query):
        return _router().classify(query)

    def expert_search(self, query, top_k=5):
        domain = self.route(query)
        graph = _router().get_expert_graph(domain)
        return [
            {
                "workflow_id": wf.get("workflow_id"),
                "project_name": wf.get("project_name"),
                "project_type": wf.get("project_type"),
                "node_count": len(wf.get("nodes", [])),
            }
            for wf in graph.get("workflows", [])[:top_k]
        ]

    def feedback(self, query, workflow_id, success, metadata=None):
        _memory().anchor(query, workflow_id, success, metadata=metadata)

    def best_for(self, query, top_k=3):
        return [wid for wid, _ in _memory().best_for_query(query, top_k=top_k)]

    def learn_manifests(self):
        aml = _manifest()
        aml.extract_all()
        return {
            "manifests_found": len(aml._manifests),
            "roles": aml.list_roles(),
            "capabilities": aml.list_capabilities(),
            "tools": aml.list_tools(),
            "merged": aml.merge_manifests(),
        }

    def benchmark(self, workflow_id=None, domain=None):
        bench = _benchmark()
        if workflow_id:
            return [bench.test_workflow(workflow_id)]
        if domain:
            return bench.test_domain(domain)
        return bench.test_all(limit=50)

    def leaderboard(self, domain=None):
        return _benchmark().leaderboard(domain=domain)

    def cycle(self, user_query, execute_code=False):
        t0 = time.time()
        domain = self.route(user_query)
        candidates = self.search(user_query, top_k=5, use_memory=True)
        top_skill = None
        if candidates:
            c = candidates[0]
            top_wid = c.get("workflow_id") or c.get("id")
            if c.get("type") == "FILE" and c.get("metadata", {}).get("workflow_id"):
                top_wid = c["metadata"]["workflow_id"]
            if top_wid:
                top_skill = self.acquire(top_wid)
        project_names = []
        for c in candidates[:3]:
            pn = c.get("metadata", {}).get("project_name") if c.get("type") == "FILE" else c.get("project_name")
            if pn:
                project_names.append(pn)
        if not project_names and top_skill:
            project_names.append(top_skill.project_name)
        prompt = self.few_shot(
            instruction=user_query,
            workflow_ids=([top_skill.workflow_id] if top_skill else []) if not project_names else None,
            project_names=project_names if project_names else None,
            domain=domain,
            shots=3,
        )
        execution_result = None
        if execute_code and top_skill and top_skill.code_snippets:
            execution_result = self.execute(top_skill.workflow_id, cell=0)
        return {
            "query": user_query,
            "domain": domain,
            "candidates": [
                {
                    "id": (c.get("metadata", {}).get("workflow_id") if c.get("type") == "FILE" else None) or c.get("workflow_id", c.get("id")),
                    "label": c.get("label", c.get("project_name")),
                    "score": c.get("similarity", c.get("boosted_score", 0)),
                }
                for c in candidates
            ],
            "acquired_skill": top_skill.to_dict() if top_skill else None,
            "prompt_length": len(prompt),
            "prompt": prompt,
            "execution": execution_result,
            "elapsed": round(time.time() - t0, 3),
        }

    def _save_skill_cache(self):
        self._skill_cache_path.write_text(
            json.dumps({wid: s.to_dict() for wid, s in self._skills.items()}, indent=2),
            encoding="utf-8",
        )

    def _load_skill_cache(self):
        if not self._skill_cache_path.exists():
            return
        try:
            for wid, info in json.loads(self._skill_cache_path.read_text(encoding="utf-8")).items():
                self._skills[wid] = Skill(
                    wid, info["project_name"], info["project_type"], [], info.get("metadata", {})
                )
        except Exception:
            pass

    def _fallback_search(self, query, limit=10):
        tokens = [t for t in query.lower().split() if len(t) >= 3]
        if not tokens:
            tokens = [query.lower()]
        full_q = query.lower()
        generic_names = {"test", "scripts", "problem_", "common", "lib", "core", "other", "web", "idle", "utils", "helpers"}
        results = []
        for f in self.projects_dir.glob("*.workflow.json"):
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            pn = wf.get("project_name", "").lower()
            matched_tokens = set()
            token_scores = []
            for q in tokens:
                token_score = 0
                pt = wf.get("project_type", "").lower()
                # Heavy weight for project_name containing the token
                if q in pn:
                    token_score += 50
                    matched_tokens.add(q)
                # Moderate weight for project_type
                if q in pt:
                    token_score += 20
                    matched_tokens.add(q)
                # Check nodes (labels + content) — cap low to avoid giant files dominating
                for node in wf.get("nodes", []):
                    label = node.get("label", "").lower()
                    if q in label:
                        token_score += 3
                        matched_tokens.add(q)
                    c = node.get("content", {})
                    if c.get("type") == "text":
                        raw = c.get("content", "")
                        if isinstance(raw, list):
                            raw = " ".join(str(x) for x in raw)
                        content = str(raw).lower()
                        hits = content.count(q)
                        if hits:
                            matched_tokens.add(q)
                            token_score += 1  # capped at 1 per node per token
                token_scores.append(token_score)
            if not matched_tokens:
                continue
            # Base score: distinct token matches matter more than raw count
            score = len(matched_tokens) * 40 + sum(token_scores)
            # Bonus when ALL tokens match
            if len(matched_tokens) == len(tokens):
                score += 100
            # Huge bonus if full query appears in project_name
            if full_q in pn:
                score += 200
            # Penalty for generic names so focused projects rank higher
            if any(g in pn for g in generic_names):
                score -= 40
            results.append(
                {
                    "workflow_id": wf.get("workflow_id", f.stem),
                    "label": wf.get("project_name", f.stem),
                    "similarity": min(max(score, 0) / 100, 1.0),
                }
            )
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]












