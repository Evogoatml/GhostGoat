"""
HuggingFace Dataset Bridge
===========================

Downloads and normalises math / algebra / numeric HF datasets into a
unified format that the rest of GhostGoat can consume directly:

    MathSample(problem, solution, domain, difficulty, rationale, tags)

Supported datasets
------------------
Dataset                         Domain              Size
──────────────────────────────  ──────────────────  ──────
EleutherAI/hendrycks_math       competition math    12,500
openai/gsm8k                    word problems       8,500
aqua_rat                        algebra rationale   100,000
deepmind/math_dataset           symbolic math       2M+
numglue                         numeric reasoning   101,000
math_qa                         math word ops       37,000

All datasets are cached locally after first download.
Streaming mode available for large datasets (deepmind/math_dataset).

Usage
-----
    # self-import removed

    bridge = HFBridge(cache_dir="./data/hf_cache")

    # Pull algebra problems
    samples = bridge.load("algebra", limit=500)

    # Pull from a specific dataset
    samples = bridge.load_dataset("openai/gsm8k", split="train", limit=200)

    # Iterate a huge dataset without loading into RAM
    for sample in bridge.stream("deepmind/math_dataset", config="algebra__easy"):
        process(sample)
"""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import Generator, Iterator, List, Optional

logger = logging.getLogger(__name__)

# ── Sample ────────────────────────────────────────────────────────────────────

@dataclass
class MathSample:
    problem:    str
    solution:   str
    domain:     str = "general"
    difficulty: str = "unknown"
    rationale:  str = ""
    tags:       List[str] = field(default_factory=list)
    source:     str = ""

    def to_skill_entry(self) -> dict:
        """Format for SkillLibrary.record()"""
        return {
            "task": self.problem,
            "solution": self.solution,
            "success": True,
            "metadata": {
                "domain": self.domain,
                "difficulty": self.difficulty,
                "source": self.source,
                "tags": self.tags,
            }
        }

    def to_knowledge_entry(self) -> dict:
        """Format for KnowledgeTank / SemanticKnowledgeTank"""
        return {
            "name": self.problem[:80],
            "description": self.solution[:400],
            "category": self.domain,
            "complexity": self.difficulty,
            "use_cases": self.tags,
            "examples": [self.rationale] if self.rationale else [],
            "source": self.source,
        }


# ── Dataset configs ───────────────────────────────────────────────────────────

# Maps friendly domain names → list of (hf_name, hf_config, split, parser_fn_name)
DATASET_REGISTRY = {
    "algebra": [
        ("EleutherAI/hendrycks_math", "algebra",     "train", "_parse_hendrycks"),
        ("aqua_rat",                  "raw",          "train", "_parse_aqua"),
        ("deepmind/math_dataset",     "algebra__easy","train", "_parse_deepmind"),
    ],
    "arithmetic": [
        ("deepmind/math_dataset", "arithmetic__add_or_sub",   "train", "_parse_deepmind"),
        ("deepmind/math_dataset", "arithmetic__mul_div_mixed", "train", "_parse_deepmind"),
        ("openai/gsm8k",          "main",                     "train", "_parse_gsm8k"),
    ],
    "calculus": [
        ("EleutherAI/hendrycks_math", "precalculus", "train", "_parse_hendrycks"),
        ("EleutherAI/hendrycks_math", "calculus",    "train", "_parse_hendrycks"),
    ],
    "number_theory": [
        ("EleutherAI/hendrycks_math", "number_theory", "train", "_parse_hendrycks"),
        ("deepmind/math_dataset",     "numbers__div_remainder", "train", "_parse_deepmind"),
    ],
    "geometry": [
        ("EleutherAI/hendrycks_math", "geometry",  "train", "_parse_hendrycks"),
        ("EleutherAI/hendrycks_math", "prealgebra", "train", "_parse_hendrycks"),
    ],
    "word_problems": [
        ("openai/gsm8k", "main",     "train", "_parse_gsm8k"),
        ("math_qa",      "default",  "train", "_parse_mathqa"),
    ],
    "numeric_reasoning": [
        ("numglue",  "all",  "train", "_parse_numglue"),
        ("math_qa",  "default", "train", "_parse_mathqa"),
    ],
    "competition": [
        ("EleutherAI/hendrycks_math", "counting_and_probability", "train", "_parse_hendrycks"),
        ("EleutherAI/hendrycks_math", "intermediate_algebra",     "train", "_parse_hendrycks"),
        ("EleutherAI/hendrycks_math", "algebra",                  "test",  "_parse_hendrycks"),
    ],
}


# ── Bridge ────────────────────────────────────────────────────────────────────

class HFBridge:
    """
    Unified HuggingFace dataset loader for math/numeric datasets.
    All loaded samples are normalised to MathSample.
    """

    def __init__(self, cache_dir: str = "./data/hf_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        os.environ.setdefault("HF_DATASETS_CACHE", cache_dir)

    # ── public API ────────────────────────────────────────────────────────────

    def load(self, domain: str, limit: int = 500,
             shuffle: bool = True) -> List[MathSample]:
        """
        Load samples for a domain (algebra, arithmetic, calculus, etc.).
        Pulls from all registered datasets for that domain and merges.
        """
        if domain not in DATASET_REGISTRY:
            raise ValueError(f"Unknown domain '{domain}'. "
                             f"Available: {list(DATASET_REGISTRY.keys())}")
        samples: List[MathSample] = []
        configs = DATASET_REGISTRY[domain]
        per_source = max(1, limit // len(configs))

        for ds_name, config, split, parser in configs:
            try:
                chunk = self._load_one(ds_name, config, split, parser,
                                       limit=per_source)
                samples.extend(chunk)
                logger.info("[HFBridge] %s/%s → %d samples", ds_name, config, len(chunk))
            except Exception as e:
                logger.warning("[HFBridge] failed to load %s/%s: %s", ds_name, config, e)

        if shuffle:
            import random
            random.shuffle(samples)
        return samples[:limit]

    def load_dataset(self, dataset_name: str, split: str = "train",
                     config: Optional[str] = None, limit: int = 500) -> List[MathSample]:
        """Load a specific HF dataset by name."""
        parser = self._detect_parser(dataset_name)
        return self._load_one(dataset_name, config or "default", split, parser, limit)

    def stream(self, dataset_name: str, config: Optional[str] = None,
               split: str = "train") -> Generator[MathSample, None, None]:
        """
        Stream a large dataset without loading into RAM.
        Yields MathSample one at a time.
        """
        from datasets import load_dataset as hf_load
        parser = self._detect_parser(dataset_name)
        parser_fn = getattr(self, parser)
        ds = hf_load(dataset_name, name=config, split=split,
                     streaming=True, cache_dir=self.cache_dir)
        for row in ds:
            sample = parser_fn(row, dataset_name)
            if sample:
                yield sample

    def available_domains(self) -> List[str]:
        return list(DATASET_REGISTRY.keys())

    def dataset_info(self) -> dict:
        return {domain: [f"{d}/{c}" for d, c, _, _ in configs]
                for domain, configs in DATASET_REGISTRY.items()}

    # ── internal loader ───────────────────────────────────────────────────────

    def _load_one(self, ds_name: str, config: str, split: str,
                  parser: str, limit: int) -> List[MathSample]:
        from datasets import load_dataset as hf_load
        parser_fn = getattr(self, parser)
        try:
            ds = hf_load(ds_name, name=config if config != "default" else None,
                         split=split, cache_dir=self.cache_dir)
        except Exception:
            # Fallback: try without config
            ds = hf_load(ds_name, split=split, cache_dir=self.cache_dir)

        samples = []
        for row in ds:
            if len(samples) >= limit:
                break
            sample = parser_fn(row, ds_name)
            if sample and sample.problem and sample.solution:
                samples.append(sample)
        return samples

    def _detect_parser(self, dataset_name: str) -> str:
        name_lower = dataset_name.lower()
        if "hendrycks" in name_lower or "hendrycks_math" in name_lower:
            return "_parse_hendrycks"
        if "gsm8k" in name_lower:
            return "_parse_gsm8k"
        if "aqua" in name_lower:
            return "_parse_aqua"
        if "deepmind" in name_lower or "math_dataset" in name_lower:
            return "_parse_deepmind"
        if "numglue" in name_lower:
            return "_parse_numglue"
        if "math_qa" in name_lower:
            return "_parse_mathqa"
        return "_parse_generic"

    # ── parsers (one per dataset schema) ─────────────────────────────────────

    def _parse_hendrycks(self, row: dict, source: str) -> Optional[MathSample]:
        """EleutherAI/hendrycks_math schema: problem, solution, level, type"""
        problem  = row.get("problem", "")
        solution = row.get("solution", "")
        level    = row.get("level", "unknown")
        typ      = row.get("type", "math")
        if not problem or not solution:
            return None
        # Extract boxed answer from solution if present
        answer = solution
        if "\\boxed{" in solution:
            start = solution.rfind("\\boxed{") + 7
            end   = solution.find("}", start)
            if end > start:
                answer = solution[start:end]
        return MathSample(
            problem=problem, solution=solution,
            domain=typ.lower().replace(" ", "_"),
            difficulty=str(level).lower(),
            rationale=solution,
            tags=[typ, str(level)],
            source=source,
        )

    def _parse_gsm8k(self, row: dict, source: str) -> Optional[MathSample]:
        """openai/gsm8k schema: question, answer"""
        q = row.get("question", "")
        a = row.get("answer", "")
        if not q or not a:
            return None
        # GSM8K answers contain chain-of-thought before ####
        rationale = ""
        final_ans = a
        if "####" in a:
            parts = a.split("####")
            rationale = parts[0].strip()
            final_ans = parts[1].strip() if len(parts) > 1 else a
        return MathSample(
            problem=q, solution=final_ans,
            domain="word_problems", difficulty="grade_school",
            rationale=rationale,
            tags=["word_problem", "arithmetic", "chain_of_thought"],
            source=source,
        )

    def _parse_aqua(self, row: dict, source: str) -> Optional[MathSample]:
        """aqua_rat schema: question, options, rationale, correct"""
        q        = row.get("question", "")
        options  = row.get("options", [])
        rational = row.get("rationale", "")
        correct  = row.get("correct", "")
        if not q:
            return None
        opts_str = " | ".join(options) if isinstance(options, list) else str(options)
        return MathSample(
            problem=f"{q}\nOptions: {opts_str}",
            solution=correct,
            domain="algebra", difficulty="medium",
            rationale=rational,
            tags=["multiple_choice", "algebra", "rationale"],
            source=source,
        )

    def _parse_deepmind(self, row: dict, source: str) -> Optional[MathSample]:
        """deepmind/math_dataset schema: question, answer"""
        q = str(row.get("question", "")).strip()
        a = str(row.get("answer", "")).strip()
        if not q or not a:
            return None
        return MathSample(
            problem=q, solution=a,
            domain="symbolic_math", difficulty="variable",
            tags=["symbolic", "deepmind"],
            source=source,
        )

    def _parse_numglue(self, row: dict, source: str) -> Optional[MathSample]:
        """numglue schema: question, answer, type"""
        q = row.get("question", "") or row.get("Question", "")
        a = row.get("answer",   "") or row.get("Answer",   "")
        t = row.get("type",     "") or row.get("Type",     "numeric")
        if not q or not a:
            return None
        return MathSample(
            problem=str(q), solution=str(a),
            domain="numeric_reasoning", difficulty="medium",
            tags=["numeric", str(t)],
            source=source,
        )

    def _parse_mathqa(self, row: dict, source: str) -> Optional[MathSample]:
        """math_qa schema: Problem, options, Rationale, correct"""
        q  = row.get("Problem", "")
        opts = row.get("options", "")
        rat  = row.get("Rationale", "")
        ans  = row.get("correct", "")
        if not q:
            return None
        return MathSample(
            problem=f"{q}\n{opts}", solution=str(ans),
            domain="math_operations", difficulty="medium",
            rationale=str(rat),
            tags=["word_problem", "operations"],
            source=source,
        )

    def _parse_generic(self, row: dict, source: str) -> Optional[MathSample]:
        """Fallback parser — tries common field names."""
        for q_key in ("question", "problem", "input", "text", "query"):
            for a_key in ("answer", "solution", "output", "target", "label"):
                q = row.get(q_key, "")
                a = row.get(a_key, "")
                if q and a:
                    return MathSample(
                        problem=str(q), solution=str(a),
                        domain="general", difficulty="unknown",
                        source=source,
                    )
        return None
