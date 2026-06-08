"""
Knowledge Seeder — bootstraps GhostGoat's skill library and knowledge systems
from structured training files in data/knowledge/.

Run once after installation, or re-run to refresh/add new seed data.

Usage
-----
    python -m core.skills.seeder               # seed everything
    python -m core.skills.seeder --force       # overwrite existing skills
    python -m core.skills.seeder --stats       # show current library stats
    python -m core.skills.seeder --list        # list top 20 skills

What it seeds
-------------
1. Skill Library   ← data/knowledge/agent_skills_seed.json
   Pre-populates ~/.ghostgoat/skills/library.json with proven task→solution
   pairs so the Agent K cache is not cold on first use.

2. Domain Knowledge (future KnowledgeTank integration)
   ← data/knowledge/domain_knowledge.json
   Structured agent capability profiles and routing rules loaded into memory
   for inspection and future KnowledgeTank indexing.

3. Orchestration Patterns (future Brain integration)
   ← data/knowledge/orchestration_patterns.json
   Proven task decomposition templates available for retrieval during planning.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# Resolve paths relative to the repo root regardless of cwd
_REPO_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_DIR = _REPO_ROOT / "data" / "knowledge"

SEED_FILES = {
    "skills":                _KNOWLEDGE_DIR / "agent_skills_seed.json",
    "domain_knowledge":      _KNOWLEDGE_DIR / "domain_knowledge.json",
    "orchestration_patterns":_KNOWLEDGE_DIR / "orchestration_patterns.json",
}


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_skill_library(force: bool = False) -> dict:
    """Seed the Agent K skill library from agent_skills_seed.json."""
    from core.brain.agents.tool_agent import SkillLibrary

    path = SEED_FILES["skills"]
    if not path.exists():
        logger.warning("Skill seed file not found: %s", path)
        return {"status": "skipped", "reason": "file not found"}

    library = SkillLibrary()
    before = library.get_stats()["total_skills"]
    added = library.seed_from_file(str(path), overwrite=force)
    after = library.get_stats()["total_skills"]

    logger.info(
        "Skill library: %d → %d skills (+%d new, %d boosted)",
        before, after, added, (after - before - added) if after > before else 0,
    )
    return {
        "status": "ok",
        "before": before,
        "after": after,
        "added": added,
        "storage": library.path,
    }


def load_domain_knowledge() -> dict:
    """Load and validate domain_knowledge.json — returns the parsed dict."""
    path = SEED_FILES["domain_knowledge"]
    if not path.exists():
        logger.warning("Domain knowledge file not found: %s", path)
        return {}

    with open(path) as fh:
        data = json.load(fh)

    domains = list(data.get("domains", {}).keys())
    routing_rules = len(data.get("routing_rules", []))
    logger.info(
        "Domain knowledge loaded: %d domains (%s), %d routing rules",
        len(domains), ", ".join(domains), routing_rules,
    )
    return data


def load_orchestration_patterns() -> list:
    """Load and validate orchestration_patterns.json — returns the parsed list."""
    path = SEED_FILES["orchestration_patterns"]
    if not path.exists():
        logger.warning("Orchestration patterns file not found: %s", path)
        return []

    with open(path) as fh:
        patterns = json.load(fh)

    names = [p.get("pattern_name", "?") for p in patterns]
    total_steps = sum(len(p.get("subtasks", [])) for p in patterns)
    logger.info(
        "Orchestration patterns loaded: %d patterns (%d total steps): %s",
        len(patterns), total_steps, ", ".join(names),
    )
    return patterns


def seed_all(force: bool = False) -> dict:
    """Run all seed operations and return a summary."""
    results = {}

    logger.info("=" * 60)
    logger.info("GhostGoat Knowledge Seeder")
    logger.info("=" * 60)

    logger.info("\n[1/3] Seeding skill library...")
    results["skills"] = seed_skill_library(force=force)

    logger.info("\n[2/3] Loading domain knowledge...")
    domain_data = load_domain_knowledge()
    results["domain_knowledge"] = {
        "status": "ok" if domain_data else "skipped",
        "domains": list(domain_data.get("domains", {}).keys()),
        "routing_rules": len(domain_data.get("routing_rules", [])),
    }

    logger.info("\n[3/3] Loading orchestration patterns...")
    patterns = load_orchestration_patterns()
    results["orchestration_patterns"] = {
        "status": "ok" if patterns else "skipped",
        "count": len(patterns),
        "patterns": [p.get("pattern_name") for p in patterns],
    }

    logger.info("\n" + "=" * 60)
    logger.info("Seeding complete.")
    logger.info("=" * 60)
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Seed GhostGoat knowledge systems from training files"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing skills with seed data (default: skip duplicates)"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print current skill library statistics and exit"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List top 20 skills by use count and exit"
    )
    parser.add_argument(
        "--patterns", action="store_true",
        help="List available orchestration pattern names and exit"
    )
    return parser.parse_args()


def main():
    # Ensure repo root is on the path so `core.skills` imports work
    sys.path.insert(0, str(_REPO_ROOT))

    args = _parse_args()

    if args.stats:
        from core.brain.agents.tool_agent import SkillLibrary
        stats = SkillLibrary().get_stats()
        print(json.dumps(stats, indent=2))
        return

    if args.list:
        from core.brain.agents.tool_agent import SkillLibrary
        skills = SkillLibrary().list_skills(limit=20)
        for i, s in enumerate(skills, 1):
            print(f"{i:2d}. [{s['success_count']}x] {s['task_signature'][:80]}")
        return

    if args.patterns:
        patterns = load_orchestration_patterns()
        for p in patterns:
            steps = len(p.get("subtasks", []))
            print(f"  {p['pattern_name']:<35} ({steps} steps) — {p['description'][:60]}")
        return

    results = seed_all(force=args.force)
    print("\nSummary:")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
