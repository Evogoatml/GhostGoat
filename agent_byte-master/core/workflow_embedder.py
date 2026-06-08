"""
WorkflowEmbedder
================

Lightweight semantic text embeddings for workflow content.
Uses token-level hashing + corpus TF-IDF weighting.
No external ML dependencies beyond numpy.

Usage:
    from core.workflow_embedder import WorkflowEmbedder
    embedder = WorkflowEmbedder(dim=128)
    embedder.fit_on_corpus(list_of_texts)
    vec = embedder.embed("import tensorflow as tf")
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


class WorkflowEmbedder:
    """Hashing + TF-IDF embedder for code and text."""

    def __init__(self, dim: int = 128):
        self.dim = dim
        self.idf: Dict[str, float] = {}
        self._avg_len = 0.0

    # ── fitting ───────────────────────────────────────────────────────────────

    def fit_on_corpus(self, texts: List[str]):
        """Compute IDF weights over a corpus of documents."""
        doc_freq: Counter = Counter()
        total_len = 0
        n_docs = 0

        for text in texts:
            tokens = self._tokenize(text)
            if not tokens:
                continue
            doc_freq.update(set(tokens))
            total_len += len(tokens)
            n_docs += 1

        self._avg_len = total_len / n_docs if n_docs else 1.0
        self.idf = {
            token: math.log((1 + n_docs) / (1 + freq)) + 1.0
            for token, freq in doc_freq.items()
        }

    def fit_on_workflows(self, projects_dir: Path):
        """Convenience: fit on all workflow JSON files in a directory."""
        texts = []
        for wf_file in projects_dir.glob("*.workflow.json"):
            wf = json.loads(wf_file.read_text(encoding="utf-8"))
            for node in wf.get("nodes", []):
                content = node.get("content", {})
                if content.get("type") == "text":
                    texts.append(content.get("content", ""))
            texts.append(wf.get("project_name", ""))
            texts.append(wf.get("project_type", ""))
        self.fit_on_corpus(texts)

    # ── embedding ─────────────────────────────────────────────────────────────

    def embed(self, text: str) -> List[float]:
        """Return a normalized dense vector for *text*."""
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dim

        # TF-IDF weighted token vectors
        counts = Counter(tokens)
        token_vecs = []
        weights = []

        for token, count in counts.items():
            tf = math.sqrt(count)  # sublinear tf scaling
            idf = self.idf.get(token, 1.0)
            token_vecs.append(self._hash_vector(token))
            weights.append(tf * idf)

        # Weighted average
        weights = np.array(weights, dtype=np.float32)
        vecs = np.array(token_vecs, dtype=np.float32)
        vec = np.average(vecs, axis=0, weights=weights)

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> List[str]:
        return TOKEN_RE.findall(text.lower())

    def _hash_vector(self, token: str) -> np.ndarray:
        """Deterministic hash of a token to a dense unit-norm vector."""
        h = hashlib.sha256(token.encode("utf-8")).hexdigest()
        vec = np.zeros(self.dim, dtype=np.float32)
        for i in range(self.dim):
            # Use 4 hex digits at a time for better variance
            idx = (i * 4) % (len(h) - 4)
            chunk = h[idx : idx + 4]
            val = int(chunk, 16) / 65535.0
            vec[i] = val - 0.5  # center around 0
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

