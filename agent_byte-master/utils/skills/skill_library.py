"""
Agent K Skill Library
=====================

Implements the core idea from the Agent-K paper: agents should acquire,
store, and *reuse* skills rather than re-solving every task from scratch.

A **skill** is a (task description → solution) pair that has been confirmed
to work at least once.  On subsequent tasks that are sufficiently similar,
the library returns the stored solution instead of calling the LLM.

Architecture
------------
* Storage   : JSON file at ``~/.ghostgoat/skills/library.json`` (configurable).
              Keeps at most ``max_skills`` entries; evicts least-recently-used.
* Retrieval : Token-overlap similarity (no external dependencies).
              If ``sentence-transformers`` is installed, upgrades to cosine
              similarity over sentence embeddings automatically.
* Integration: Hook into ``LLMOrchestrator._execute_task()`` — check before
              calling the Brain/LLM, record after a successful run.

Confidence
----------
Each skill has a ``confidence`` float [0, 1] derived from:
    confidence = success_count / (success_count + fail_count)

Only skills above the configurable ``min_confidence`` threshold are returned
by ``lookup()``.  New skills start at confidence 1.0 and decay on failures.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.path.expanduser("~/.ghostgoat/skills/library.json")
_DEFAULT_MAX_SKILLS = 500
_DEFAULT_MIN_CONFIDENCE = 0.6
_DEFAULT_SIMILARITY_THRESHOLD = 0.35


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    """A stored skill: task description → proven solution."""

    task_signature: str          # normalised task description used as key
    solution: str                # the output that worked
    success_count: int = 1
    fail_count: int = 0
    last_used: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    @property
    def confidence(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total else 1.0

    @property
    def use_count(self) -> int:
        return self.success_count + self.fail_count

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Skill":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> set:
    """Lowercase word tokens, punctuation stripped."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _token_overlap(a: str, b: str) -> float:
    """Jaccard similarity between token sets."""
    ta, tb = _tokenise(a), _tokenise(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# Try to load sentence-transformers for better similarity
_encoder = None

def _get_encoder():
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        from sentence_transformers import SentenceTransformer
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.debug("SkillLibrary: using sentence-transformers for similarity")
    except ImportError:
        _encoder = False
        logger.debug("SkillLibrary: sentence-transformers not found, using token overlap")
    return _encoder


def _similarity(a: str, b: str) -> float:
    enc = _get_encoder()
    if enc:
        import numpy as np
        va, vb = enc.encode([a, b])
        denom = (np.linalg.norm(va) * np.linalg.norm(vb))
        return float(np.dot(va, vb) / denom) if denom else 0.0
    return _token_overlap(a, b)


# ---------------------------------------------------------------------------
# Skill Library
# ---------------------------------------------------------------------------

class SkillLibrary:
    """
    Persistent skill store with similarity-based retrieval.

    Parameters
    ----------
    path : str
        Path to the JSON file used for persistence.
    max_skills : int
        Maximum number of skills to retain (LRU eviction beyond this).
    min_confidence : float
        Minimum skill confidence required for ``lookup()`` to return a hit.
    similarity_threshold : float
        Minimum similarity score [0, 1] for a task to match a stored skill.
    """

    def __init__(
        self,
        path: str = _DEFAULT_PATH,
        max_skills: int = _DEFAULT_MAX_SKILLS,
        min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
        similarity_threshold: float = _DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self.path = path
        self.max_skills = max_skills
        self.min_confidence = min_confidence
        self.similarity_threshold = similarity_threshold
        self._skills: Dict[str, Skill] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(self, task_description: str) -> Optional[Skill]:
        """Return the best matching skill, or None if no good match.

        A match is returned only when:
          * similarity >= similarity_threshold
          * skill.confidence >= min_confidence
        """
        best_skill: Optional[Skill] = None
        best_score = -1.0

        for skill in self._skills.values():
            if skill.confidence < self.min_confidence:
                continue
            score = _similarity(task_description, skill.task_signature)
            if score > best_score:
                best_score = score
                best_skill = skill

        if best_skill and best_score >= self.similarity_threshold:
            best_skill.last_used = time.time()
            self._save()
            logger.info(
                "SkillLibrary HIT (score=%.2f, conf=%.2f): %s",
                best_score,
                best_skill.confidence,
                best_skill.task_signature[:60],
            )
            return best_skill

        return None

    def record(
        self,
        task_description: str,
        solution: str,
        success: bool = True,
        tags: Optional[List[str]] = None,
    ) -> Skill:
        """Store or update a skill based on a task execution result.

        If a very similar skill already exists (above threshold) it is updated
        in-place.  Otherwise a new skill is created.
        """
        existing = self.lookup(task_description)
        if existing:
            if success:
                existing.success_count += 1
                # Update solution only when the new one is non-trivial
                if len(solution) > len(existing.solution):
                    existing.solution = solution
            else:
                existing.fail_count += 1
            existing.last_used = time.time()
            self._save()
            return existing

        # New skill
        sig = self._normalise(task_description)
        skill = Skill(
            task_signature=sig,
            solution=solution,
            success_count=1 if success else 0,
            fail_count=0 if success else 1,
            tags=tags or [],
        )
        self._skills[sig] = skill
        self._evict_if_needed()
        self._save()
        logger.info("SkillLibrary NEW skill: %s", sig[:60])
        return skill

    def delete(self, task_signature: str) -> bool:
        """Remove a skill by its normalised signature."""
        if task_signature in self._skills:
            del self._skills[task_signature]
            self._save()
            return True
        return False

    def get_stats(self) -> dict:
        skills = list(self._skills.values())
        return {
            "total_skills": len(skills),
            "avg_confidence": (
                sum(s.confidence for s in skills) / len(skills) if skills else 0.0
            ),
            "total_uses": sum(s.use_count for s in skills),
            "storage_path": self.path,
        }

    def seed_from_file(self, path: str, overwrite: bool = False) -> int:
        """Load seed skills from a JSON file into the library.

        The JSON file should be a list of objects with at minimum:
          - "task"     : task description (required)
          - "solution" : known good solution (required)
          - "confidence_boost" : int — pre-confirmed success count (optional, default 5)
          - "tags"     : list of strings (optional)

        Args:
            path: Path to the seed JSON file.
            overwrite: If True, overwrite existing skills with matching signatures.
                       If False (default), skip entries that already exist.

        Returns:
            Number of new skills added.
        """
        try:
            with open(path) as fh:
                entries = json.load(fh)
        except Exception as exc:
            logger.error("seed_from_file: failed to load %s — %s", path, exc)
            return 0

        added = 0
        for entry in entries:
            task = entry.get("task") or entry.get("task_signature")
            solution = entry.get("solution")
            if not task or not solution:
                continue

            sig = self._normalise(task)
            boost = int(entry.get("confidence_boost", 5))

            if sig in self._skills and not overwrite:
                self._skills[sig].success_count += boost
                continue

            skill = Skill(
                task_signature=sig,
                solution=solution,
                success_count=boost,
                fail_count=0,
                tags=entry.get("tags", []),
            )
            self._skills[sig] = skill
            added += 1

        self._evict_if_needed()
        self._save()
        logger.info("seed_from_file: added %d skills from %s", added, path)
        return added

    def list_skills(self, limit: int = 20) -> List[dict]:
        """Return top skills sorted by use count descending."""
        sorted_skills = sorted(
            self._skills.values(), key=lambda s: s.use_count, reverse=True
        )
        return [s.to_dict() for s in sorted_skills[:limit]]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        """Produce a stable, lowercased signature from a task description."""
        return re.sub(r"\s+", " ", text.lower().strip())[:200]

    def _evict_if_needed(self):
        """Remove least-recently-used skills when over capacity."""
        if len(self._skills) <= self.max_skills:
            return
        overflow = len(self._skills) - self.max_skills
        lru = sorted(self._skills.items(), key=lambda kv: kv[1].last_used)
        for key, _ in lru[:overflow]:
            del self._skills[key]
        logger.debug("SkillLibrary: evicted %d LRU skills", overflow)

    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path) as fh:
                raw = json.load(fh)
            self._skills = {k: Skill.from_dict(v) for k, v in raw.items()}
            logger.debug("SkillLibrary: loaded %d skills from %s", len(self._skills), self.path)
        except Exception as exc:
            logger.warning("SkillLibrary: failed to load %s — %s", self.path, exc)
            self._skills = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as fh:
                json.dump({k: v.to_dict() for k, v in self._skills.items()}, fh, indent=2)
        except Exception as exc:
            logger.warning("SkillLibrary: failed to save — %s", exc)
