"""
Math Knowledge Seeder
======================

Pulls HuggingFace math datasets and injects them into three places:

1. SkillLibrary     — problem→solution pairs Agent K recalls without LLM calls
2. KnowledgeTank    — structured mathematical knowledge for semantic search
3. MemoryController — vector embeddings so agents find similar past problems

Run once on startup (or on demand) to warm up the system with mathematical
knowledge before any user tasks arrive.  Subsequent runs skip already-seen
problems via a bloom-filter-style hash set.

Usage
-----
    from core.bridges.hf_bridge import MathSeeder
    seeder = MathSeeder()
    await seeder.seed_all()          # seeds everything
    await seeder.seed_domain("algebra", limit=1000)
    report = seeder.report()
"""
from __future__ import annotations
import asyncio
import hashlib
import logging
import os
from typing import Dict, List, Optional, Set

from core.datasets.hf_bridge import HFBridge, MathSample

logger = logging.getLogger(__name__)


class MathSeeder:
    """
    Seeds the GhostGoat knowledge systems from HuggingFace math datasets.
    Idempotent: re-running skips problems already loaded (via seen-hash set).
    """

    DEFAULT_LIMITS: Dict[str, int] = {
        "algebra":          800,
        "arithmetic":       600,
        "calculus":         400,
        "number_theory":    400,
        "geometry":         300,
        "word_problems":    600,
        "numeric_reasoning": 500,
        "competition":      300,
    }

    def __init__(self,
                 cache_dir: str = "./data/hf_cache",
                 seen_file: str = "./data/math_seeder_seen.txt"):
        self.bridge = HFBridge(cache_dir=cache_dir)
        self.seen_file = seen_file
        self._seen: Set[str] = self._load_seen()
        self._counts: Dict[str, int] = {}

    # ── public API ────────────────────────────────────────────────────────────

    async def seed_all(self, limits: Optional[Dict[str, int]] = None):
        """Seed all domains. Runs concurrently."""
        lims = limits or self.DEFAULT_LIMITS
        tasks = [
            asyncio.ensure_future(self.seed_domain(domain, limit))
            for domain, limit in lims.items()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._save_seen()
        logger.info("[MathSeeder] seeded %d total samples",
                    sum(self._counts.values()))

    async def seed_domain(self, domain: str, limit: int = 500):
        """Seed a single domain from HuggingFace."""
        logger.info("[MathSeeder] loading domain: %s (limit=%d)", domain, limit)
        loop = asyncio.get_event_loop()
        try:
            samples = await loop.run_in_executor(
                None, lambda: self.bridge.load(domain, limit=limit)
            )
        except Exception as e:
            logger.warning("[MathSeeder] failed to load %s: %s", domain, e)
            return

        new_samples = [s for s in samples if not self._is_seen(s)]
        logger.info("[MathSeeder] %s: %d new / %d total", domain,
                    len(new_samples), len(samples))

        for sample in new_samples:
            await self._inject(sample)
            self._mark_seen(sample)

        self._counts[domain] = self._counts.get(domain, 0) + len(new_samples)

    async def seed_from_stream(self, dataset_name: str, config: str,
                                limit: int = 2000):
        """Seed from a streaming dataset (for large ones like deepmind/math_dataset)."""
        logger.info("[MathSeeder] streaming %s/%s (limit=%d)", dataset_name, config, limit)
        count = 0
        for sample in self.bridge.stream(dataset_name, config=config):
            if count >= limit:
                break
            if not self._is_seen(sample):
                await self._inject(sample)
                self._mark_seen(sample)
                count += 1
        self._save_seen()
        logger.info("[MathSeeder] streamed %d samples from %s", count, dataset_name)

    # ── injection ─────────────────────────────────────────────────────────────

    async def _inject(self, sample: MathSample):
        """Inject one sample into all three knowledge systems."""
        loop = asyncio.get_event_loop()
        await asyncio.gather(
            loop.run_in_executor(None, self._inject_skill_library, sample),
            loop.run_in_executor(None, self._inject_knowledge_tank, sample),
            loop.run_in_executor(None, self._inject_memory,        sample),
            return_exceptions=True,
        )

    def _inject_skill_library(self, sample: MathSample):
        try:
            from core.brain.agents import tool_agent as skill_library
            entry = sample.to_skill_entry()
            skill_library.record(
                task=entry["task"],
                solution=entry["solution"],
                success=True,
            )
        except Exception as e:
            logger.debug("[MathSeeder] skill_library inject error: %s", e)

    def _inject_knowledge_tank(self, sample: MathSample):
        try:
            from core.memory.semantic_tank import KnowledgeTank
            kt = KnowledgeTank()
            entry = sample.to_knowledge_entry()
            kt.add_algorithm(
                name=entry["name"],
                description=entry["description"],
                category=entry["category"],
                complexity=entry["complexity"],
                use_cases=entry["use_cases"],
                examples=entry["examples"],
            )
        except Exception as e:
            logger.debug("[MathSeeder] knowledge_tank inject error: %s", e)

    def _inject_memory(self, sample: MathSample):
        try:
            from core.controllers.memory_controller import memory
            content = f"Problem: {sample.problem}\nSolution: {sample.solution}"
            if sample.rationale:
                content += f"\nRationale: {sample.rationale}"
            memory.remember(content, agent_id="math_seeder", metadata={
                "domain": sample.domain,
                "difficulty": sample.difficulty,
                "source": sample.source,
                "tags": sample.tags,
                "type": "math_knowledge",
            })
        except Exception as e:
            logger.debug("[MathSeeder] memory inject error: %s", e)

    # ── deduplication ─────────────────────────────────────────────────────────

    def _hash(self, sample: MathSample) -> str:
        return hashlib.md5(sample.problem[:200].encode()).hexdigest()

    def _is_seen(self, sample: MathSample) -> bool:
        return self._hash(sample) in self._seen

    def _mark_seen(self, sample: MathSample):
        self._seen.add(self._hash(sample))

    def _load_seen(self) -> Set[str]:
        if os.path.exists(self.seen_file):
            with open(self.seen_file) as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _save_seen(self):
        os.makedirs(os.path.dirname(self.seen_file) or ".", exist_ok=True)
        with open(self.seen_file, "w") as f:
            f.write("\n".join(self._seen))

    # ── reporting ─────────────────────────────────────────────────────────────

    def report(self) -> Dict:
        return {
            "domains_seeded": list(self._counts.keys()),
            "counts": self._counts,
            "total": sum(self._counts.values()),
            "seen_hashes": len(self._seen),
        }
