"""TrainingPipeline — generates fine-tuning datasets from workflow code."""
from __future__ import annotations
import json, random
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path(
    "/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows/projects"
)
TEMPLATES = [
    "Write a Python function that implements {description}.",
    "Implement {description} in Python.",
    "Create a {project_type} solution for {description}.",
    "Given the context below, write code to {description}.",
    "Solve this problem: {description}",
    "Refactor the following into a clean implementation of {description}.",
]


class TrainingPipeline:
    def __init__(self, projects_dir=None):
        self.projects_dir = projects_dir or PROJECTS_DIR

    def extract_pairs(self, domain=None, min_code_lines=5, max_code_chars=2000):
        pairs = []
        for f in self.projects_dir.glob("*.workflow.json"):
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if domain and wf.get("project_type") != domain:
                continue
            pn = wf.get("project_name", "")
            pt = wf.get("project_type", "")
            desc = self._infer_description(wf)
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
                            if cell.get("cell_type") != "code":
                                continue
                            code = "".join(cell.get("source", [])).strip()
                            if (
                                code.count("\n") < min_code_lines
                                or len(code) > max_code_chars
                            ):
                                continue
                            inst = self._build_instruction(pn, pt, desc)
                            if (
                                i > 0
                                and nb["cells"][i - 1].get("cell_type") == "markdown"
                            ):
                                md = (
                                    "".join(nb["cells"][i - 1].get("source", []))
                                    .strip()
                                )
                                if md:
                                    inst = f"{inst}\n\nContext: {md[:500]}"
                            pairs.append(
                                {
                                    "instruction": inst,
                                    "input": "",
                                    "output": code,
                                    "source": f.stem,
                                }
                            )
                    except Exception:
                        pass
                elif ext == ".py":
                    code = raw.strip()
                    if (
                        code.count("\n") >= min_code_lines
                        and len(code) <= max_code_chars
                    ):
                        pairs.append(
                            {
                                "instruction": self._build_instruction(pn, pt, desc),
                                "input": "",
                                "output": code,
                                "source": f.stem,
                            }
                        )
        return pairs

    def build_alpaca_dataset(self, domain=None, max_pairs=1000):
        pairs = self.extract_pairs(domain=domain)
        random.shuffle(pairs)
        return [
            {"instruction": p["instruction"], "input": p["input"], "output": p["output"]}
            for p in pairs[:max_pairs]
        ]

    def build_sharegpt_dataset(self, domain=None, max_pairs=1000):
        pairs = self.extract_pairs(domain=domain)
        random.shuffle(pairs)
        return [
            {
                "messages": [
                    {"role": "system", "content": "You are a helpful coding assistant."},
                    {"role": "user", "content": p["instruction"]},
                    {
                        "role": "assistant",
                        "content": f"```python\n{p['output']}\n```",
                    },
                ]
            }
            for p in pairs[:max_pairs]
        ]

    def build_sft_dataset(self, domain=None, system_prompt=None, max_pairs=1000):
        pairs = self.extract_pairs(domain=domain)
        random.shuffle(pairs)
        sp = system_prompt or "You are an expert Python developer."
        return [
            {
                "messages": [
                    {"role": "system", "content": sp},
                    {"role": "user", "content": p["instruction"]},
                    {"role": "assistant", "content": p["output"]},
                ]
            }
            for p in pairs[:max_pairs]
        ]

    def build_completion_dataset(self, domain=None, max_pairs=1000):
        pairs = self.extract_pairs(domain=domain)
        random.shuffle(pairs)
        return [
            {"prompt": p["instruction"], "completion": p["output"]}
            for p in pairs[:max_pairs]
        ]

    @staticmethod
    def export_jsonl(dataset, path):
        with open(path, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Exported {len(dataset)} examples to {path}")

    @staticmethod
    def export_json(dataset, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Exported {len(dataset)} examples to {path}")

    def get_corpus_stats(self):
        total_files = code_files = notebook_files = total_lines = 0
        domains = set()
        for f in self.projects_dir.glob("*.workflow.json"):
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            domains.add(wf.get("project_type", "unknown"))
            for node in wf.get("nodes", []):
                ext = node["metadata"].get("extension", "")
                if ext in (".py", ".ipynb"):
                    total_files += 1
                    if ext == ".py":
                        code_files += 1
                    else:
                        notebook_files += 1
                    content = node.get("content", {})
                    if content.get("type") == "text":
                        raw = content.get("content", "")
                        if ext == ".ipynb":
                            try:
                                nb = json.loads(raw)
                                for cell in nb.get("cells", []):
                                    if cell.get("cell_type") == "code":
                                        total_lines += len(cell.get("source", []))
                            except Exception:
                                pass
                        else:
                            total_lines += raw.count("\n")
        return {
            "projects": len(list(self.projects_dir.glob("*.workflow.json"))),
            "code_files": code_files,
            "notebook_files": notebook_files,
            "total_files": total_files,
            "total_code_lines": total_lines,
            "domains": sorted(domains),
        }

    @staticmethod
    def _build_instruction(pn, pt, desc):
        return random.choice(TEMPLATES).format(
            description=desc or pn.replace("_", " "), project_type=pt or "software"
        )

    @staticmethod
    def _infer_description(wf):
        n = wf.get("project_name", "").replace("_", " ")
        t = wf.get("project_type", "")
        return f"{t.replace('_', ' ')}: {n}" if t else n
