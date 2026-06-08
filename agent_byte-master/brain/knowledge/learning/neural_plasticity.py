"""
Neural Plasticity Engine
=========================

Prevents the neuro-system from ossifying.  Left unchecked, feedback loops
always converge: confidence → 1.0, stability → 1.0, check_interval → 120s,
and the system stops learning.  This engine counteracts that with three
mechanisms borrowed from biological neural plasticity research:

1. Forgetting Curves (Ebbinghaus decay)
   ─────────────────────────────────────
   Confidence and stability decay exponentially with time unless a skill /
   state is actively *used*.  A skill last used 30 days ago should not have
   the same weight as one used yesterday.

       confidence(t) = confidence₀ × e^(-λ × days_since_use)

   λ (decay_rate) is tuned per component:
     - SkillLibrary: λ = 0.02  (slow — skills are expensive to re-learn)
     - NeuralCore stability: λ = 0.05  (medium)
     - MetaGodelAgent consistency scores: λ = 0.10  (fast — should re-check often)

2. Entropy Injection
   ──────────────────
   Periodically perturbs high-confidence items so the system is forced to
   re-verify them.  Items whose confidence > HIGH_CONF_THRESHOLD get a small
   random perturbation added, ensuring they stay in the "re-validate" zone.

       if confidence > 0.92:
           confidence -= random.uniform(0.05, 0.15)

   This is analogous to synaptic noise in biological neurons.

3. Curiosity Drive
   ────────────────
   Tracks how often each domain / skill category was *used* vs *explored*.
   When one domain dominates (exploitation bias), the drive schedules
   forced exploration of under-used domains, feeding those paths back into
   the MathSeeder / BuildLoop / SelfBuilder.

All three mechanisms run in a background thread (default: every 6 hours).
State is persisted to data/plasticity_state.json so decay continues across
restarts.

Usage
-----
    from core.brain.agent_core.reasoning_core import plasticity
    plasticity.start()           # background thread
    plasticity.run_cycle()       # manual one-shot
    plasticity.status()          # current stats
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import threading
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

HIGH_CONF_THRESHOLD    = 0.92   # above this → entropy injection candidate
ENTROPY_DROP_MIN       = 0.05
ENTROPY_DROP_MAX       = 0.15
DECAY_SKILL            = 0.02   # per-day Ebbinghaus λ for skill library
DECAY_STABILITY        = 0.05   # per-day λ for neural-core stability
DECAY_CONSISTENCY      = 0.10   # per-day λ for Gödel consistency scores
MIN_CONFIDENCE         = 0.30   # floor — never decay below this
CURIOSITY_IMBALANCE    = 3.0    # trigger exploration if top/bottom domain ratio > 3×
STATE_PATH             = "data/plasticity_state.json"
CYCLE_INTERVAL_HOURS   = 6


# ── State ─────────────────────────────────────────────────────────────────────

@dataclass
class PlasticityState:
    last_run_ts:        float = 0.0
    cycles:             int   = 0
    skills_decayed:     int   = 0
    skills_perturbed:   int   = 0
    stability_decays:   int   = 0
    curiosity_triggers: int   = 0
    domain_use_counts:  Dict[str, int]   = field(default_factory=dict)
    entropy_log:        List[str]        = field(default_factory=list)  # last 20

    def add_log(self, msg: str):
        self.entropy_log.append(f"{datetime.now(timezone.utc).isoformat()}: {msg}")
        self.entropy_log = self.entropy_log[-20:]


# ── Engine ────────────────────────────────────────────────────────────────────

class NeuralPlasticity:
    """
    Background engine that keeps the neuro-system plastic (learnable).
    Prevents confidence/stability metrics from freezing at 1.0.
    """

    def __init__(self, state_path: str = STATE_PATH,
                 cycle_hours: float = CYCLE_INTERVAL_HOURS):
        self.state_path  = state_path
        self.cycle_secs  = cycle_hours * 3600
        self._state      = self._load_state()
        self._thread: Optional[threading.Thread] = None
        self._stop       = threading.Event()

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        """Start the background plasticity thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="neural-plasticity"
        )
        self._thread.start()
        logger.info("[Plasticity] background thread started (cycle=%.0fh)",
                    self.cycle_secs / 3600)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def run_cycle(self):
        """Run one full plasticity cycle (blocking). Called by the thread."""
        logger.info("[Plasticity] cycle %d starting", self._state.cycles + 1)
        self._decay_skill_library()
        self._decay_neural_core()
        self._decay_godel_consistency()
        self._inject_entropy()
        self._apply_curiosity_drive()
        self._state.cycles += 1
        self._state.last_run_ts = time.time()
        self._save_state()
        logger.info("[Plasticity] cycle done — decayed=%d perturbed=%d",
                    self._state.skills_decayed, self._state.skills_perturbed)

    def record_domain_use(self, domain: str, count: int = 1):
        """Call this whenever a domain/skill is used — feeds curiosity tracking."""
        self._state.domain_use_counts[domain] = (
            self._state.domain_use_counts.get(domain, 0) + count
        )

    def status(self) -> dict:
        return {
            **asdict(self._state),
            "next_run_in_mins": max(0, (
                self._state.last_run_ts + self.cycle_secs - time.time()
            ) / 60),
        }

    # ── decay: skill library ──────────────────────────────────────────────────

    def _decay_skill_library(self):
        """Apply Ebbinghaus decay to SkillLibrary confidence scores."""
        try:
            from core.brain.agents.tool_agent import SkillLibrary
            lib = SkillLibrary()
            now = time.time()
            decayed = 0
            for skill in lib.list_skills():
                days = (now - skill.last_used) / 86400
                if days < 1:
                    continue  # used recently — no decay
                new_conf = _ebbinghaus(skill.confidence, days, DECAY_SKILL)
                if new_conf < skill.confidence - 0.001:
                    skill.confidence = max(MIN_CONFIDENCE, new_conf)
                    lib._save()   # persist
                    decayed += 1
            self._state.skills_decayed += decayed
            if decayed:
                self._state.add_log(f"Decayed {decayed} skill(s) in SkillLibrary")
            logger.info("[Plasticity] SkillLibrary: %d skills decayed", decayed)
        except Exception as e:
            logger.debug("[Plasticity] skill decay error: %s", e)

    # ── decay: neural core stability ──────────────────────────────────────────

    def _decay_neural_core(self):
        """Prevent NeuralCore.stability from freezing at 1.0."""
        try:
            from core.brain.agent_core.reasoning_core import NeuralCore
            nc = NeuralCore()
            state = nc.introspect()
            stability = state.get("stability", 0.5)
            if stability > 0.85:
                # Decay back toward 0.85 over time so adaptation never stops
                delta = (stability - 0.85) * DECAY_STABILITY
                new_stab = max(0.85, stability - delta)
                nc._state["stability"] = new_stab
                nc._save()
                self._state.stability_decays += 1
                self._state.add_log(
                    f"NeuralCore stability decayed {stability:.3f}→{new_stab:.3f}"
                )
                logger.info("[Plasticity] NeuralCore stability capped: %.3f→%.3f",
                            stability, new_stab)
        except Exception as e:
            logger.debug("[Plasticity] neural_core decay error: %s", e)

    # ── decay: Gödel consistency scores ──────────────────────────────────────

    def _decay_godel_consistency(self):
        """
        Clear stale Gödel consistency scores from ChromaDB so the agent
        re-verifies answers instead of assuming they're still correct.
        Items older than 7 days with consistency > 0.8 get their score reset.
        """
        try:
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            col_names = [c.name for c in client.list_collections()]
            if "agent_memory" not in col_names:
                return
            col = client.get_collection("agent_memory")
            cutoff = time.time() - 7 * 86400
            results = col.get(include=["metadatas", "documents"],
                              where={"type": {"$eq": "godel_consistency"}})
            if not results["ids"]:
                return
            stale_ids = []
            for i, meta in enumerate(results["metadatas"]):
                ts  = float(meta.get("timestamp", 0))
                sc  = float(meta.get("consistency_score", 0))
                if ts < cutoff and sc > 0.8:
                    stale_ids.append(results["ids"][i])
            if stale_ids:
                col.delete(ids=stale_ids)
                self._state.add_log(
                    f"Cleared {len(stale_ids)} stale Gödel consistency records"
                )
                logger.info("[Plasticity] cleared %d stale Gödel records", len(stale_ids))
        except Exception as e:
            logger.debug("[Plasticity] godel decay error: %s", e)

    # ── entropy injection ─────────────────────────────────────────────────────

    def _inject_entropy(self):
        """
        Perturb high-confidence skills (>0.92) so they stay in the
        re-validation zone.  Prevents the skill library from becoming
        a static lookup table.
        """
        try:
            from core.brain.agents.tool_agent import SkillLibrary
            lib = SkillLibrary()
            perturbed = 0
            for skill in lib.list_skills():
                if skill.confidence > HIGH_CONF_THRESHOLD:
                    drop = random.uniform(ENTROPY_DROP_MIN, ENTROPY_DROP_MAX)
                    skill.confidence = max(MIN_CONFIDENCE, skill.confidence - drop)
                    perturbed += 1
            if perturbed:
                lib._save()
                self._state.skills_perturbed += perturbed
                self._state.add_log(
                    f"Entropy: perturbed {perturbed} skills above {HIGH_CONF_THRESHOLD}"
                )
                logger.info("[Plasticity] entropy injection: %d skills perturbed", perturbed)
        except Exception as e:
            logger.debug("[Plasticity] entropy inject error: %s", e)

    # ── curiosity drive ───────────────────────────────────────────────────────

    def _apply_curiosity_drive(self):
        """
        Detect exploitation bias — when one domain is used >> others.
        Schedule exploration of under-used domains via MathSeeder.
        """
        counts = self._state.domain_use_counts
        if len(counts) < 2:
            return
        max_count  = max(counts.values())
        min_count  = min(counts.values())
        if min_count == 0 or (max_count / min_count) < CURIOSITY_IMBALANCE:
            return  # balanced enough

        under_used = [d for d, c in counts.items() if c == min_count]
        logger.info("[Plasticity] curiosity triggered — under-used domains: %s",
                    under_used)
        self._state.curiosity_triggers += 1
        self._state.add_log(
            f"Curiosity: scheduling exploration of {under_used} "
            f"(imbalance ratio={max_count/min_count:.1f}x)"
        )

        # Trigger async seeding for under-used math domains
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                from core.bridges.hf_bridge import MathSeeder
                seeder = MathSeeder()
                for domain in under_used:
                    asyncio.ensure_future(seeder.seed_domain(domain, limit=200))
        except Exception as e:
            logger.debug("[Plasticity] curiosity seeding error: %s", e)

        # Also re-open top BuildLoop gaps for re-examination
        self._reopen_stale_build_gaps()

    def _reopen_stale_build_gaps(self):
        """
        BuildLoop marks gaps ✅ and never revisits them.
        Re-open gaps that were marked resolved > 30 days ago so the
        system re-validates its own wiring periodically.
        """
        log_path = "data/build_loop_log.json"
        if not os.path.exists(log_path):
            return
        try:
            with open(log_path) as f:
                log = json.load(f)
            cutoff = time.time() - 30 * 86400
            reopened = 0
            for entry in log:
                if (entry.get("status") == "resolved"
                        and entry.get("resolved_at", 0) < cutoff):
                    entry["status"] = "pending_recheck"
                    reopened += 1
            if reopened:
                with open(log_path, "w") as f:
                    json.dump(log, f, indent=2)
                self._state.add_log(
                    f"Re-opened {reopened} stale BuildLoop gaps for re-validation"
                )
                logger.info("[Plasticity] re-opened %d BuildLoop gaps", reopened)
        except Exception as e:
            logger.debug("[Plasticity] build gap reopen error: %s", e)

    # ── thread loop ───────────────────────────────────────────────────────────

    def _loop(self):
        # Stagger first run by 30 minutes after boot
        self._stop.wait(timeout=1800)
        while not self._stop.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                logger.error("[Plasticity] cycle error: %s", e)
            self._stop.wait(timeout=self.cycle_secs)

    # ── persistence ───────────────────────────────────────────────────────────

    def _load_state(self) -> PlasticityState:
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path) as f:
                    data = json.load(f)
                return PlasticityState(**data)
            except Exception:
                pass
        return PlasticityState()

    def _save_state(self):
        with open(self.state_path, "w") as f:
            json.dump(asdict(self._state), f, indent=2)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ebbinghaus(confidence: float, days: float, decay_rate: float) -> float:
    """R = R₀ × e^(-λt)  — Ebbinghaus forgetting curve."""
    return confidence * math.exp(-decay_rate * days)


# ── singleton ─────────────────────────────────────────────────────────────────

plasticity = NeuralPlasticity()
