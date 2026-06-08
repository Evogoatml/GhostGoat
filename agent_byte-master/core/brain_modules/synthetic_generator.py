"""SyntheticGenerator — generates synthetic code variations for data augmentation."""
from __future__ import annotations
import ast, json, random, re
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path(
    "/home/popic/GhostGoat/agent_byte-master/brain/knowledge/processed/workflows/projects"
)
VAR_POOL = [
    "x",
    "y",
    "z",
    "a",
    "b",
    "c",
    "data",
    "result",
    "output",
    "value",
    "item",
    "elem",
    "obj",
    "node",
    "edge",
]
LIB_SWAPS = {
    "tensorflow": ["torch", "jax"],
    "tf.": ["torch.", "F."],
    "keras": ["torch.nn", "sklearn"],
    "np.": ["torch.", "jnp."],
    "pandas": ["polars", "pyarrow"],
    "sklearn": ["torch", "tensorflow"],
}


class SyntheticGenerator:
    def __init__(self, projects_dir=None, seed=None):
        self.projects_dir = projects_dir or PROJECTS_DIR
        if seed is not None:
            random.seed(seed)

    @staticmethod
    def mutate_rename(code):
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code
        names = {
            n.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Name)
            and isinstance(n.ctx, ast.Store)
            and n.id not in {"self", "cls", "_", "args", "kwargs"}
        }
        if not names:
            return code
        mapping = {
            n: random.choice(VAR_POOL) + str(random.randint(1, 99)) for n in names
        }
        pat = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in names) + r")\b"
        )
        return pat.sub(lambda m: mapping.get(m.group(0), m.group(0)), code)

    @staticmethod
    def mutate_library_swap(code):
        for old, alts in LIB_SWAPS.items():
            if old in code and random.random() < 0.3:
                code = code.replace(old, random.choice(alts))
        return code

    @staticmethod
    def mutate_comments(code):
        lines = code.splitlines()
        out = []
        for line in lines:
            s = line.strip()
            if s.startswith("#"):
                if random.random() < 0.3:
                    continue
                if random.random() < 0.3:
                    line = f"# {s.lstrip('#').strip().upper()}"
            out.append(line)
            if random.random() < 0.05 and s and not s.startswith("#"):
                out.append(
                    f"    # step: {random.choice(['process', 'transform', 'validate', 'compute'])}"
                )
        return "\n".join(out)

    @staticmethod
    def mutate_constants(code):
        def p(m):
            n = float(m.group(0))
            d = n * 0.1
            nv = n + random.uniform(-d, d)
            return str(int(nv)) if nv == int(nv) else f"{nv:.4f}"

        return re.sub(r"(?<!\w)\d+\.?\d*", p, code)

    @staticmethod
    def mutate_docstring(code):
        pat = r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'
        if random.random() < 0.5:
            return re.sub(
                pat,
                lambda m: f'"""{random.choice(["Auto-generated", "Refactored", "Optimized"])}."""',
                code,
            )
        return re.sub(pat, "", code)

    def mutate(self, code, strategy=None, n=1):
        strategies = ["rename", "library_swap", "comments", "constants", "docstring"]
        results = []
        for _ in range(n):
            s = strategy or random.choice(strategies)
            v = code
            if s == "rename":
                v = self.mutate_rename(v)
            elif s == "library_swap":
                v = self.mutate_library_swap(v)
            elif s == "comments":
                v = self.mutate_comments(v)
            elif s == "constants":
                v = self.mutate_constants(v)
            elif s == "docstring":
                v = self.mutate_docstring(v)
            elif s == "all":
                for st in strategies:
                    v = getattr(self, f"mutate_{st}")(v)
            results.append(v)
        return results

    def augment_workflow(self, wf, total_variations=10):
        out = []
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
                        code = "".join(cell.get("source", []))
                        for v in self.mutate(code, strategy="all", n=total_variations):
                            out.append(
                                {
                                    "source_workflow": wf.get("workflow_id"),
                                    "file": node["label"],
                                    "cell": i,
                                    "original": code,
                                    "variant": v,
                                }
                            )
                except Exception:
                    pass
            elif ext == ".py":
                for v in self.mutate(raw, strategy="all", n=total_variations):
                    out.append(
                        {
                            "source_workflow": wf.get("workflow_id"),
                            "file": node["label"],
                            "cell": 0,
                            "original": raw,
                            "variant": v,
                        }
                    )
        return out

    def build_augmented_dataset(self, workflow_ids=None, variations_per_cell=3):
        dataset = []
        files = list(self.projects_dir.glob("*.workflow.json"))
        if workflow_ids:
            files = [f for f in files if f.stem in workflow_ids]
        for f in files:
            try:
                wf = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            dataset.extend(
                self.augment_workflow(wf, total_variations=variations_per_cell)
            )
        return dataset

    @staticmethod
    def export_jsonl(dataset, path):
        with open(path, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Exported {len(dataset)} augmented examples to {path}")
