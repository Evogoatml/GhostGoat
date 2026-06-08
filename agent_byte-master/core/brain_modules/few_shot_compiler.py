"""FewShotCompiler — turns workflow JSONs into structured LLM prompts."""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path("/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows/projects")


class FewShotCompiler:
    def __init__(self, projects_dir=None, max_input_tokens=4000):
        self.projects_dir = projects_dir or PROJECTS_DIR
        self.max_chars = max_input_tokens * 4
        self._cache = {}

    def _load(self, wid):
        if wid in self._cache:
            return self._cache[wid]
        f = self.projects_dir / f"{wid}.workflow.json"
        if not f.exists():
            return None
        wf = json.loads(f.read_text(encoding="utf-8"))
        self._cache[wid] = wf
        return wf

    @staticmethod
    def extract_code_cells(wf, language="python"):
        snippets = []
        for node in wf.get("nodes", []):
            ext = node["metadata"].get("extension", "")
            content = node.get("content", {})
            if content.get("type") != "text":
                continue
            raw = content.get("content", "")
            if ext == ".ipynb":
                try:
                    nb = json.loads(raw)
                    for i, cell in enumerate(nb.get("cells", [])):
                        if cell.get("cell_type") == "code":
                            snippets.append(
                                {
                                    "file": node["label"],
                                    "cell": i,
                                    "lang": "python",
                                    "code": "".join(cell.get("source", [])),
                                    "outputs": cell.get("outputs", []),
                                }
                            )
                except Exception:
                    pass
            elif ext in (".py", ".m"):
                ld = "matlab" if ext == ".m" else "python"
                if language == "any" or ld == language:
                    snippets.append(
                        {"file": node["label"], "cell": 0, "lang": ld, "code": raw, "outputs": []}
                    )
        return snippets

    @staticmethod
    def extract_markdown(wf):
        docs = []
        for node in wf.get("nodes", []):
            ext = node["metadata"].get("extension", "")
            content = node.get("content", {})
            if content.get("type") != "text":
                continue
            raw = content.get("content", "")
            if ext == ".ipynb":
                try:
                    nb = json.loads(raw)
                    for cell in nb.get("cells", []):
                        if cell.get("cell_type") == "markdown":
                            docs.append("".join(cell.get("source", [])))
                except Exception:
                    pass
            elif ext in (".md", ".txt", ".rst"):
                docs.append(raw)
        return docs

    def build_prompt(
        self,
        instruction,
        workflow_ids=None,
        project_names=None,
        domain=None,
        shots=3,
        include_tests=False,
        chain_of_thought=False,
        system_message=None,
    ):
        # Build candidate list first so we know if we have examples
        candidates = []
        if workflow_ids:
            for wid in workflow_ids:
                wf = self._load(wid)
                if wf:
                    candidates.append(wf)
        elif project_names:
            for name in project_names:
                for f in self.projects_dir.glob("*.workflow.json"):
                    wf = json.loads(f.read_text(encoding="utf-8"))
                    if wf.get("project_name") == name:
                        candidates.append(wf)
                        break
        else:
            for f in self.projects_dir.glob("*.workflow.json"):
                wf = json.loads(f.read_text(encoding="utf-8"))
                if domain and wf.get("project_type") != domain:
                    continue
                candidates.append(wf)

        candidates.sort(key=lambda w: self._relevance_score(w, instruction), reverse=True)
        candidates = candidates[:shots]

        # If no examples found, return clean instruction without boilerplate
        if not candidates:
            return f"[INSTRUCTION]\n{instruction}\n\n[OUTPUT]\n```python\n"

        parts = []
        total_len = 0
        if system_message:
            parts.append(f"[SYSTEM]\n{system_message}\n")
            total_len += len(parts[-1])

        parts.append(f"[INSTRUCTION]\n{instruction}\n\n[EXAMPLES]\n")
        total_len += len(parts[-2]) + len(parts[-1])

        for wf in candidates:
            cells = self.extract_code_cells(wf, "python")
            docs = self.extract_markdown(wf)
            if not cells and not docs:
                continue
            block = f"\n# Example: {wf.get('project_name', 'unknown')}\n"
            if docs:
                block += f"# Context: {docs[0][:200]}...\n"
            for cell in cells[:2]:
                block += f"```python\n{cell['code'][:800]}\n```\n"
            if total_len + len(block) > self.max_chars:
                break
            parts.append(block)
            total_len += len(block)

        if include_tests:
            tb = self._build_test_block(candidates)
            if total_len + len(tb) <= self.max_chars:
                parts.append(tb)

        if chain_of_thought:
            parts.append("\n[REASONING]\nLet's think step by step.\n")
        parts.append("\n[OUTPUT]\n```python\n")
        return "".join(parts)

    def build_chat_messages(self, instruction, workflow_ids=None, shots=3, system_message=None):
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})

        candidates = []
        if workflow_ids:
            for wid in workflow_ids:
                wf = self._load(wid)
                if wf:
                    candidates.append(wf)
        candidates.sort(key=lambda w: self._relevance_score(w, instruction), reverse=True)
        candidates = candidates[:shots]

        for wf in candidates:
            cells = self.extract_code_cells(wf, "python")
            if not cells:
                continue
            messages.append(
                {"role": "user", "content": f"Write {wf.get('project_name', 'code')}:"}
            )
            messages.append(
                {"role": "assistant", "content": f"```python\n{cells[0]['code'][:1000]}\n```"}
            )

        messages.append({"role": "user", "content": instruction})
        return messages

    @staticmethod
    def _relevance_score(wf, instruction):
        q = instruction.lower()
        score = 0
        score += wf.get("project_name", "").lower().count(q) * 3
        score += wf.get("project_type", "").lower().count(q) * 2
        for node in wf.get("nodes", []):
            score += node.get("label", "").lower().count(q)
            c = node.get("content", {})
            if c.get("type") == "text":
                score += c.get("content", "").lower().count(q)
        return score

    @staticmethod
    def _build_test_block(candidates):
        lines = ["\n[TESTS TO PASS]\n"]
        for wf in candidates:
            for node in wf.get("nodes", []):
                if node["metadata"].get("extension") in (".py", ".ipynb"):
                    raw = node.get("content", {}).get("content", "")
                    if "assert" in raw or "test" in raw.lower():
                        lines.append(f"# From {wf.get('project_name')}:\n")
                        for line in raw.splitlines():
                            if "assert" in line or line.strip().startswith("def test_"):
                                lines.append(line + "\n")
                        break
        return "".join(lines)

