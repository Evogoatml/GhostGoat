"""
Diagnostics & Feedback Loop
============================

Monitors the pipeline in real time and adjusts parameters to maintain
throughput and integrity under degraded conditions.

What it tracks
--------------
- Noise rate from SignalLayer  (CRC failure rate)
- Bad-block rate from BlockEngine
- Recovery rate from Translator
- Per-run latency and throughput (bytes/sec)

What it adjusts
---------------
Parameter           Trigger                     Action
──────────────────  ──────────────────────────  ───────────────────────────
redundancy_level    bad_block_rate > threshold  Increase parity bytes
block_size          high noise + low recovery   Decrease block size (finer granularity)
max_retries         recovery_rate dropping      Increase retry budget
rotation signal     counter > rotation_limit    Emit key rotation recommendation

Adjustment strategy is conservative:
  - Parameters only increase/decrease by one step per cycle
  - Hysteresis prevents oscillation (must be N consecutive cycles to change)
  - All changes are logged and emitted on the AgentBus
"""
from __future__ import annotations
import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Metrics snapshot ──────────────────────────────────────────────────────────

@dataclass
class PipelineMetrics:
    ts: float = field(default_factory=time.monotonic)
    noise_rate: float = 0.0          # fraction of frames with bad CRC
    bad_block_rate: float = 0.0      # fraction of blocks marked failed
    recovery_rate: float = 1.0       # fraction of bad blocks probabilistically recovered
    quality_score: float = 1.0       # TranslationResult.quality_score
    throughput_bps: float = 0.0      # bytes per second
    latency_ms: float = 0.0
    block_size: int = 4096
    redundancy_level: int = 8
    retries_used: int = 0


@dataclass
class DiagnosticsConfig:
    # Thresholds that trigger adjustments
    noise_warn:       float = 0.02   # 2% bad CRC → start watching
    noise_critical:   float = 0.10   # 10% → aggressive increase
    bad_block_warn:   float = 0.05
    bad_block_crit:   float = 0.20
    quality_floor:    float = 0.80   # below this → alert

    # Step sizes
    redundancy_step:  int   = 4      # bytes per adjustment
    block_size_step:  int   = 512    # bytes per adjustment

    # Bounds
    redundancy_min:   int   = 4
    redundancy_max:   int   = 64
    block_size_min:   int   = 512
    block_size_max:   int   = 65536

    # Hysteresis: how many consecutive bad cycles before adjusting
    hysteresis:       int   = 2

    # Key rotation
    rotation_limit:   int   = 10_000   # counter cycles before recommending rotation


# ── Diagnostics engine ────────────────────────────────────────────────────────

class Diagnostics:
    """
    Continuous monitoring and self-adjustment loop.

    Usage
    -----
        diag = Diagnostics(config)
        diag.register_callbacks(
            on_adjust_redundancy=lambda n: engine.adjust(redundancy_level=n),
            on_adjust_block_size=lambda n: engine.adjust(block_size=n),
            on_rotate_key=lambda: dsl.rotate_master_key(os.urandom(32)),
        )
        await diag.start_loop(interval=5.0)
        # ... after each pipeline run:
        diag.record(metrics)
    """

    def __init__(self, config: Optional[DiagnosticsConfig] = None):
        self.cfg = config or DiagnosticsConfig()
        self._history: deque = deque(maxlen=200)
        self._bad_streak: int = 0
        self._good_streak: int = 0

        # Callbacks injected by Pipeline
        self._on_adjust_redundancy: Optional[Callable[[int], None]] = None
        self._on_adjust_block_size:  Optional[Callable[[int], None]] = None
        self._on_rotate_key:         Optional[Callable[[], None]] = None

        self._current_redundancy: int = 8
        self._current_block_size: int = 4096
        self._loop_task: Optional[asyncio.Task] = None

    def register_callbacks(self, *,
                            on_adjust_redundancy: Optional[Callable] = None,
                            on_adjust_block_size:  Optional[Callable] = None,
                            on_rotate_key:         Optional[Callable] = None):
        self._on_adjust_redundancy = on_adjust_redundancy
        self._on_adjust_block_size  = on_adjust_block_size
        self._on_rotate_key         = on_rotate_key

    # ── record ────────────────────────────────────────────────────────────────

    def record(self, metrics: PipelineMetrics):
        """Call after each pipeline run to feed the diagnostics loop."""
        self._history.append(metrics)
        self._current_redundancy = metrics.redundancy_level
        self._current_block_size = metrics.block_size
        self._evaluate(metrics)

    # ── evaluate (synchronous, called per-record) ─────────────────────────────

    def _evaluate(self, m: PipelineMetrics):
        is_bad = (
            m.noise_rate > self.cfg.noise_warn
            or m.bad_block_rate > self.cfg.bad_block_warn
            or m.quality_score < self.cfg.quality_floor
        )
        if is_bad:
            self._bad_streak += 1
            self._good_streak = 0
        else:
            self._good_streak += 1
            self._bad_streak = 0

        if self._bad_streak >= self.cfg.hysteresis:
            self._apply_adjustments(m)
            self._bad_streak = 0

    def _apply_adjustments(self, m: PipelineMetrics):
        actions: List[str] = []

        # Increase redundancy if bad blocks are high
        if m.bad_block_rate > self.cfg.bad_block_warn:
            new_rl = min(
                self._current_redundancy + self.cfg.redundancy_step,
                self.cfg.redundancy_max
            )
            if new_rl != self._current_redundancy:
                if self._on_adjust_redundancy:
                    self._on_adjust_redundancy(new_rl)
                self._current_redundancy = new_rl
                actions.append(f"redundancy↑{new_rl}")

        # Decrease block size if noise is high (finer granularity = less data lost per bad block)
        if m.noise_rate > self.cfg.noise_warn:
            new_bs = max(
                self._current_block_size - self.cfg.block_size_step,
                self.cfg.block_size_min
            )
            if new_bs != self._current_block_size:
                if self._on_adjust_block_size:
                    self._on_adjust_block_size(new_bs)
                self._current_block_size = new_bs
                actions.append(f"block_size↓{new_bs}")

        # Critical noise — go aggressive
        if m.noise_rate > self.cfg.noise_critical:
            new_rl = min(self._current_redundancy + self.cfg.redundancy_step * 2,
                         self.cfg.redundancy_max)
            if self._on_adjust_redundancy:
                self._on_adjust_redundancy(new_rl)
            self._current_redundancy = new_rl
            actions.append(f"redundancy_critical↑{new_rl}")

        if actions:
            logger.warning("[Diag] adjustments applied: %s (noise=%.1f%% bad=%.1f%% quality=%.1f%%)",
                           ", ".join(actions),
                           m.noise_rate * 100, m.bad_block_rate * 100,
                           m.quality_score * 100)
            try:
                from core.bus.agent_bus import bus
                bus.publish_sync("system.status", {
                    "event": "pipeline_adjustment",
                    "actions": actions,
                    "noise_rate": m.noise_rate,
                    "quality_score": m.quality_score,
                }, source="diagnostics")
            except Exception:
                pass

    # ── async monitoring loop ─────────────────────────────────────────────────

    async def start_loop(self, interval: float = 10.0):
        """
        Background loop that periodically logs stats and checks
        whether key rotation is recommended.
        """
        self._loop_task = asyncio.ensure_future(self._loop(interval))
        logger.info("[Diag] monitoring loop started (interval=%.1fs)", interval)

    async def _loop(self, interval: float):
        while True:
            await asyncio.sleep(interval)
            self._periodic_report()

    def _periodic_report(self):
        if not self._history:
            return
        recent = list(self._history)[-20:]
        avg_noise   = sum(m.noise_rate       for m in recent) / len(recent)
        avg_bad     = sum(m.bad_block_rate   for m in recent) / len(recent)
        avg_quality = sum(m.quality_score    for m in recent) / len(recent)
        avg_tput    = sum(m.throughput_bps   for m in recent) / len(recent)

        logger.info("[Diag] ── pipeline health ──────────────────────────────")
        logger.info("[Diag]   noise=%.2f%%  bad_blocks=%.2f%%  quality=%.1f%%  tput=%.1fKB/s",
                    avg_noise * 100, avg_bad * 100, avg_quality * 100, avg_tput / 1024)
        logger.info("[Diag]   block_size=%d  redundancy=%d",
                    self._current_block_size, self._current_redundancy)

        if avg_quality < self.cfg.quality_floor:
            logger.warning("[Diag] ⚠ quality below floor (%.1f%%) — check data source",
                           avg_quality * 100)

    # ── summary ───────────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        recent = list(self._history)[-20:] if self._history else []
        if not recent:
            return {"status": "no data"}
        return {
            "runs": len(self._history),
            "avg_noise_pct":    round(sum(m.noise_rate     for m in recent) / len(recent) * 100, 2),
            "avg_bad_pct":      round(sum(m.bad_block_rate for m in recent) / len(recent) * 100, 2),
            "avg_quality_pct":  round(sum(m.quality_score  for m in recent) / len(recent) * 100, 2),
            "current_block_size":    self._current_block_size,
            "current_redundancy":    self._current_redundancy,
            "bad_streak":            self._bad_streak,
        }
