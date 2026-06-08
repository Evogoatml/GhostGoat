"""
Loop Guardian (Liveness Watchdog)
===================================

The neuro-system has many background loops:
  - SelfAwareLoop   (anomaly detection + self-healing)
  - BuildLoop       (auto-wiring gap filler)
  - Pipeline monitor (parameter auto-adjustment)
  - MathSeeder      (knowledge seeding)
  - NeuralPlasticity (forgetting + entropy)
  - ASI diagnostics (system metrics)

Any of these can die silently:
  - Exception in thread swallowed by daemon thread
  - asyncio task cancelled but not recreated
  - Thread finished because loop condition became permanently False
  - Check interval backed off so far it never fires again (SelfAwareLoop → 120s)

The LoopGuardian watches all of them every 60 seconds.
If a loop hasn't reported activity within its expected TTL, the guardian
restarts it and emits a warning on the AgentBus.

Each monitored loop registers itself via:
    guardian.register("loop_name", heartbeat_fn, max_silence_secs, restart_fn)

Loops call:
    guardian.heartbeat("loop_name")   # I'm alive

Guardian checks every 60s and triggers restart_fn() for any loop that
has been silent longer than max_silence_secs.

Ossification detection
-----------------------
Beyond pure liveness, the guardian also detects *functional freezing*:
a loop that is alive (heartbeating) but whose *output* has not changed.

Example: SelfAwareLoop fires every 10s but always reports "no anomalies"
for 48 hours straight — that's suspicious.  The guardian tracks output
hashes and flags loops whose outputs have been identical for too long.

This triggers a "plasticity nudge": the loop is given a new stimulus
(injecting a synthetic anomaly / forcing a re-scan) to verify it can
still detect real problems.

Usage
-----
    from core.kernel.build_loop import guardian
    guardian.start()
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

GUARDIAN_INTERVAL   = 60          # check every 60 seconds
MAX_FROZEN_CYCLES   = 48          # flag loop if output unchanged for this many checks
STATE_PATH          = "data/loop_guardian_state.json"


# ── Registered loop ────────────────────────────────────────────────────────────

@dataclass
class LoopRecord:
    name:              str
    max_silence_secs:  float
    restart_fn:        Callable
    heartbeat_fn:      Optional[Callable]    = None
    last_heartbeat_ts: float                 = field(default_factory=time.time)
    last_output_hash:  str                   = ""
    frozen_cycles:     int                   = 0
    restarts:          int                   = 0
    nudges:            int                   = 0
    alive:             bool                  = True


# ── Guardian ──────────────────────────────────────────────────────────────────

class LoopGuardian:
    """
    Watchdog that monitors all neuro-system background loops for liveness
    and functional ossification.
    """

    def __init__(self):
        self._loops:  Dict[str, LoopRecord] = {}
        self._lock    = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop    = threading.Event()
        self._history: List[dict] = []   # audit log (last 100 events)

    # ── public API ────────────────────────────────────────────────────────────

    def register(self, name: str,
                 restart_fn: Callable,
                 max_silence_secs: float = 300,
                 heartbeat_fn: Optional[Callable] = None):
        """
        Register a loop for monitoring.

        name             — unique identifier for the loop
        restart_fn       — callable that (re)starts the loop
        max_silence_secs — how long without a heartbeat before guardian restarts
        heartbeat_fn     — optional callable returning current loop output/state
                           (used for ossification detection)
        """
        with self._lock:
            self._loops[name] = LoopRecord(
                name=name,
                max_silence_secs=max_silence_secs,
                restart_fn=restart_fn,
                heartbeat_fn=heartbeat_fn,
            )
        logger.info("[Guardian] registered loop: %s (ttl=%.0fs)", name, max_silence_secs)

    def heartbeat(self, name: str, output: Optional[str] = None):
        """
        Called by a loop to signal it is alive.
        output — optional string representation of current loop state/output.
                 If provided, used for ossification detection.
        """
        with self._lock:
            if name not in self._loops:
                return
            rec = self._loops[name]
            rec.last_heartbeat_ts = time.time()
            rec.alive = True
            if output is not None:
                h = hashlib.md5(output.encode()).hexdigest()
                if h == rec.last_output_hash:
                    rec.frozen_cycles += 1
                else:
                    rec.frozen_cycles = 0
                    rec.last_output_hash = h

    def start(self):
        """Start the guardian background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="loop-guardian"
        )
        self._thread.start()
        logger.info("[Guardian] watchdog started (interval=%ds)", GUARDIAN_INTERVAL)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def status(self) -> dict:
        with self._lock:
            return {
                "loops": {
                    name: {
                        "alive": rec.alive,
                        "silence_secs": round(time.time() - rec.last_heartbeat_ts, 1),
                        "frozen_cycles": rec.frozen_cycles,
                        "restarts": rec.restarts,
                        "nudges": rec.nudges,
                    }
                    for name, rec in self._loops.items()
                },
                "total_restarts": sum(r.restarts for r in self._loops.values()),
                "total_nudges":   sum(r.nudges   for r in self._loops.values()),
                "recent_events":  self._history[-10:],
            }

    # ── check cycle ───────────────────────────────────────────────────────────

    def _check_all(self):
        now = time.time()
        with self._lock:
            records = list(self._loops.values())

        for rec in records:
            silence = now - rec.last_heartbeat_ts

            # ── liveness check ────────────────────────────────────────────────
            if silence > rec.max_silence_secs:
                self._restart(rec, silence)
                continue

            # ── heartbeat_fn check ────────────────────────────────────────────
            if rec.heartbeat_fn:
                try:
                    output = str(rec.heartbeat_fn())
                    self.heartbeat(rec.name, output)
                except Exception as e:
                    logger.warning("[Guardian] heartbeat_fn error for %s: %s",
                                   rec.name, e)

            # ── ossification check ────────────────────────────────────────────
            if rec.frozen_cycles >= MAX_FROZEN_CYCLES:
                self._nudge(rec)

    def _restart(self, rec: LoopRecord, silence: float):
        logger.warning("[Guardian] DEAD LOOP detected: %s (silent %.0fs) — restarting",
                       rec.name, silence)
        self._log_event("restart", rec.name,
                        f"silent for {silence:.0f}s > {rec.max_silence_secs:.0f}s limit")
        try:
            rec.restart_fn()
            rec.restarts += 1
            rec.last_heartbeat_ts = time.time()
            rec.alive = True
            self._publish_event("loop.restarted", {
                "loop": rec.name, "silence_secs": silence,
                "total_restarts": rec.restarts
            })
        except Exception as e:
            logger.error("[Guardian] failed to restart %s: %s", rec.name, e)
            self._log_event("restart_failed", rec.name, str(e))

    def _nudge(self, rec: LoopRecord):
        """Inject a synthetic stimulus to verify the loop can still detect changes."""
        logger.warning("[Guardian] FROZEN LOOP detected: %s (%d cycles unchanged) — nudging",
                       rec.name, rec.frozen_cycles)
        self._log_event("nudge", rec.name,
                        f"output frozen for {rec.frozen_cycles} cycles")
        rec.nudges += 1
        rec.frozen_cycles = 0   # reset so we don't nudge every cycle

        # Dispatch nudge actions per loop
        nudge_actions = {
            "self_aware_loop":  self._nudge_self_aware,
            "build_loop":       self._nudge_build_loop,
            "skill_library":    self._nudge_skill_library,
            "math_seeder":      self._nudge_math_seeder,
            "pipeline_monitor": self._nudge_pipeline,
        }
        action = nudge_actions.get(rec.name, self._nudge_generic)
        try:
            action(rec)
        except Exception as e:
            logger.debug("[Guardian] nudge action error for %s: %s", rec.name, e)

        self._publish_event("loop.nudged", {"loop": rec.name, "nudges": rec.nudges})

    # ── nudge actions (per loop type) ─────────────────────────────────────────

    def _nudge_self_aware(self, rec: LoopRecord):
        """Inject a synthetic anomaly so SelfAwareLoop has to respond."""
        try:
            from core.brain.agents.self_aware_loop import SelfAwareLoop
            loop = SelfAwareLoop()
            # Force check interval to minimum so it re-fires immediately
            if hasattr(loop, "check_interval"):
                loop.check_interval = 10
            # Inject a synthetic memory pressure anomaly for one cycle
            if hasattr(loop, "_inject_synthetic_anomaly"):
                loop._inject_synthetic_anomaly("memory_pressure")
            logger.info("[Guardian] SelfAwareLoop nudged — check_interval reset to 10s")
        except Exception as e:
            logger.debug("[Guardian] self_aware nudge: %s", e)

    def _nudge_build_loop(self, rec: LoopRecord):
        """Force BuildLoop to re-scan SYSTEM_MAP for gaps."""
        try:
            from core.kernel.build_loop import BuildLoop
            bl = BuildLoop()
            if hasattr(bl, "_force_rescan"):
                bl._force_rescan()
        except Exception as e:
            logger.debug("[Guardian] build_loop nudge: %s", e)

    def _nudge_skill_library(self, rec: LoopRecord):
        """Trigger a plasticity cycle on the skill library."""
        try:
            from core.brain.agent_core.reasoning_core import plasticity
            plasticity._inject_entropy()
        except Exception as e:
            logger.debug("[Guardian] skill_library nudge: %s", e)

    def _nudge_math_seeder(self, rec: LoopRecord):
        """Reseed an under-used math domain."""
        import asyncio
        try:
            from core.bridges.hf_bridge import MathSeeder
            seeder = MathSeeder()
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(seeder.seed_domain("competition", limit=100))
        except Exception as e:
            logger.debug("[Guardian] math_seeder nudge: %s", e)

    def _nudge_pipeline(self, rec: LoopRecord):
        """Pipeline monitor nudge — restarts the loop if it was registered."""
        self._nudge_generic(rec)

    def _nudge_generic(self, rec: LoopRecord):
        """Fallback: just restart the loop."""
        self._restart(rec, 0)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _log_event(self, kind: str, loop: str, detail: str):
        event = {"ts": time.time(), "kind": kind, "loop": loop, "detail": detail}
        self._history.append(event)
        self._history = self._history[-100:]

    def _publish_event(self, topic: str, payload: dict):
        try:
            import asyncio
            from core.bus.agent_bus import bus
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(bus.publish(topic, payload, source="guardian"))
        except Exception:
            pass

    # ── thread ────────────────────────────────────────────────────────────────

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._check_all()
            except Exception as e:
                logger.error("[Guardian] check error: %s", e)
            self._stop.wait(timeout=GUARDIAN_INTERVAL)


# ── singleton ─────────────────────────────────────────────────────────────────

guardian = LoopGuardian()
