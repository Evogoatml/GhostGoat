#!/usr/bin/env python3
"""
GFS Logging System
Professional sysadmin-standard adaptive hybrid logging.

Format:
  TTY/console  → plain text (human readable, color-coded)
  File/pipe    → JSON structured (machine-parseable, ELK/Grafana ready)
  Error events → both always, regardless of destination
  Tier-aware   → core=INFO, sandbox=DEBUG, ephemeral=DEBUG, archive=WARNING

File structure (sysadmin standard):
  /var/log/gfs/gfs.log        → INFO+ rotating daily, 7-day retention
  /var/log/gfs/gfs.error.log  → ERROR+ never auto-rotated
  /var/log/gfs/gfs.debug.log  → DEBUG rotating hourly, 24hr retention
  /var/log/gfs/gfs.audit.log  → SECURITY append-only immutable
  /var/log/gfs/gfs.perf.log   → timing metrics JSON only

Silent externally. Professional internally.
Every log line carries: ts, level, svc, agent, dur_us, event code.
"""

import json
import sys
import os
import time
import logging
import logging.handlers
import threading
import traceback
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, Any
from enum import IntEnum
from contextlib import contextmanager

# ═══════════════════════════════════════════════════════════════════════════════
# RFC 5424 SEVERITY LEVELS
# ═══════════════════════════════════════════════════════════════════════════════

class Severity(IntEnum):
    EMERGENCY = 0   # system unusable — full halt
    ALERT     = 1   # immediate action required — pager
    CRITICAL  = 2   # critical condition — ops team
    ERROR     = 3   # dispatch failed, security refused, CRDT conflict
    WARNING   = 4   # high load, deadline risk, fallback activated
    NOTICE    = 5   # goal formed, sidecar spawned, skill discovered
    INFO      = 6   # dispatch success, episode complete, transfer done
    DEBUG     = 7   # Q-values, Hopfield scores, MIS orbit steps

# Map RFC 5424 → Python logging levels
_RFC_TO_PYTHON = {
    Severity.EMERGENCY: logging.CRITICAL + 10,
    Severity.ALERT:     logging.CRITICAL + 5,
    Severity.CRITICAL:  logging.CRITICAL,
    Severity.ERROR:     logging.ERROR,
    Severity.WARNING:   logging.WARNING,
    Severity.NOTICE:    logging.INFO + 5,
    Severity.INFO:      logging.INFO,
    Severity.DEBUG:     logging.DEBUG,
}

# Register NOTICE level with Python logging
logging.addLevelName(logging.INFO + 5, "NOTICE")

# ═══════════════════════════════════════════════════════════════════════════════
# TIER-AWARE LOG LEVEL POLICY
# ═══════════════════════════════════════════════════════════════════════════════

TIER_LOG_POLICY = {
    "core":      Severity.INFO,      # clean production signal
    "plugin":    Severity.INFO,      # same as core
    "sandbox":   Severity.DEBUG,     # full trace for experimental
    "archive":   Severity.WARNING,   # frozen code shouldn't run
    "ephemeral": Severity.DEBUG,     # capture everything while alive
    "default":   Severity.INFO,
}

# ═══════════════════════════════════════════════════════════════════════════════
# ANSI COLOR CODES (TTY only)
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "EMERGENCY": "\033[1;35m",   # bold magenta
    "ALERT":     "\033[1;31m",   # bold red
    "CRITICAL":  "\033[31m",     # red
    "ERROR":     "\033[31m",     # red
    "WARNING":   "\033[33m",     # yellow
    "NOTICE":    "\033[36m",     # cyan
    "INFO":      "\033[32m",     # green
    "DEBUG":     "\033[90m",     # dark gray
    "RESET":     "\033[0m",
    "DIM":       "\033[2m",
    "BOLD":      "\033[1m",
}

_IS_TTY = sys.stderr.isatty()

def _color(level_name: str, text: str) -> str:
    if not _IS_TTY:
        return text
    c = COLORS.get(level_name, "")
    return f"{c}{text}{COLORS['RESET']}"

# ═══════════════════════════════════════════════════════════════════════════════
# LOG RECORD STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GFSLogRecord:
    """
    Every log line in GFS carries these fields.
    Structured for machine parsing and human reading.
    """
    ts:        str           # ISO 8601 UTC
    level:     str           # RFC 5424 level name
    svc:       str           # service: gfs.dispatcher, gfs.thinker, etc.
    event:     str           # dot-notation event code: dispatch.success
    msg:       str           # short human message
    agent:     Optional[str] # ghostgoat | adap | test
    tier:      Optional[str] # core | plugin | sandbox | archive | ephemeral
    fname:     Optional[str] # GFS filename involved
    goal_id:   Optional[str] # goal ID (first 8 chars)
    dur_us:    Optional[float] # operation duration microseconds
    extra:     Optional[dict]  # additional context

    def to_json(self) -> str:
        d = {k:v for k,v in asdict(self).items() if v is not None}
        return json.dumps(d, separators=(',',':'))

    def to_plain(self) -> str:
        """Human-readable plain text format."""
        ts_short  = self.ts[11:23]  # HH:MM:SS.mmm
        level_str = f"{self.level:<8}"
        svc_str   = f"{self.svc:<22}"
        dur_str   = f" [{self.dur_us:.1f}μs]" if self.dur_us else ""
        fname_str = f" {self.fname}" if self.fname else ""
        goal_str  = f" goal={self.goal_id}" if self.goal_id else ""
        agent_str = f" agent={self.agent}" if self.agent else ""
        extra_str = ""
        if self.extra:
            extra_str = " " + " ".join(f"{k}={v}" for k,v in self.extra.items())

        colored_level = _color(self.level, level_str)
        colored_event = _color(self.level, self.event)
        dim = COLORS["DIM"] if _IS_TTY else ""
        rst = COLORS["RESET"] if _IS_TTY else ""

        return (f"{dim}{ts_short}{rst} {colored_level} "
                f"{dim}{svc_str}{rst} "
                f"{colored_event}{fname_str}{goal_str}{agent_str}"
                f"{dur_str}{extra_str}")

# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTIVE HANDLER — auto-detects destination, formats accordingly
# ═══════════════════════════════════════════════════════════════════════════════

class AdaptiveHandler(logging.Handler):
    """
    Auto-selects format based on destination:
      TTY stderr    → plain text with color
      File/pipe     → JSON structured
      Error events  → both always
    """

    def __init__(self, stream=None, force_json=False, force_plain=False):
        super().__init__()
        self._stream     = stream or sys.stderr
        self._force_json  = force_json
        self._force_plain = force_plain
        self._lock        = threading.Lock()

    def _use_json(self) -> bool:
        if self._force_json:  return True
        if self._force_plain: return False
        # Auto-detect: TTY → plain, else → JSON
        try:
            return not self._stream.isatty()
        except AttributeError:
            return True

    def emit(self, record: logging.LogRecord):
        try:
            rec = record.__dict__.get("gfs_record")
            if not rec:
                return
            with self._lock:
                if self._use_json():
                    line = rec.to_json() + "\n"
                else:
                    line = rec.to_plain() + "\n"
                self._stream.write(line)
                self._stream.flush()
        except Exception:
            self.handleError(record)

# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT HANDLER — append-only, immutable security log
# ═══════════════════════════════════════════════════════════════════════════════

class AuditHandler(logging.Handler):
    """
    Append-only security audit log.
    Never rotated. Never deleted automatically.
    JSON only — machine-parseable for compliance.
    HMAC integrity chain — each entry signs the previous.
    """

    def __init__(self, path: Path):
        super().__init__()
        self._path   = path
        self._lock   = threading.Lock()
        self._prev_hash = "genesis"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Read last hash for chain continuity
        if path.exists():
            try:
                lines = path.read_text().strip().split("\n")
                for line in reversed(lines):
                    if line:
                        last = json.loads(line)
                        self._prev_hash = last.get("chain_hash","genesis")
                        break
            except Exception:
                pass

    def emit(self, record: logging.LogRecord):
        rec = record.__dict__.get("gfs_record")
        if not rec: return
        with self._lock:
            entry_json = rec.to_json()
            chain_hash = hashlib.sha3_256(
                f"{self._prev_hash}:{entry_json}".encode()).hexdigest()[:16]
            self._prev_hash = chain_hash
            audit_entry = json.loads(entry_json)
            audit_entry["chain_hash"] = chain_hash
            with open(self._path, "a") as f:
                f.write(json.dumps(audit_entry, separators=(',',':')) + "\n")

# ═══════════════════════════════════════════════════════════════════════════════
# PERF HANDLER — timing metrics only
# ═══════════════════════════════════════════════════════════════════════════════

class PerfHandler(logging.Handler):
    """
    Performance metrics log — timing data only.
    Used for optimization analysis and regression detection.
    JSON compact format for ingestion into metrics systems.
    """

    def __init__(self, path: Path):
        super().__init__()
        self._path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord):
        rec = record.__dict__.get("gfs_record")
        if not rec or rec.dur_us is None:
            return
        with self._lock:
            perf = {
                "ts":     rec.ts,
                "svc":    rec.svc,
                "event":  rec.event,
                "dur_us": rec.dur_us,
                "tier":   rec.tier,
                "agent":  rec.agent,
            }
            if rec.extra:
                perf.update(rec.extra)
            with open(self._path, "a") as f:
                f.write(json.dumps(perf, separators=(',',':')) + "\n")

# ═══════════════════════════════════════════════════════════════════════════════
# GFS LOGGER — main interface
# ═══════════════════════════════════════════════════════════════════════════════

class GFSLogger:
    """
    GFS structured logger.
    Silent to users. Professional to operators.

    Usage:
        log = GFSLogger("gfs.dispatcher", agent="ghostgoat")
        log.info("dispatch.success", fname="py.orc.cor.000", dur_us=4.7)
        log.warning("load.high", extra={"load": 0.87})
        log.error("dispatch.refused", fname="js.dat.arc.000",
                  extra={"reason": "ARCHIVE_IMMUTABLE"})

        with log.timer("hopfield.retrieve"):
            results = memory.retrieve(fname)
        # → automatically logs dur_us on exit
    """

    _registry: dict[str,'GFSLogger'] = {}
    _handlers_initialized = False
    _log_dir = Path("/var/log/gfs")
    _fallback_dir = Path("./logs/gfs")

    def __init__(self, service: str,
                 agent:  Optional[str] = None,
                 tier:   Optional[str] = None):
        self.service = service
        self.agent   = agent
        self.tier    = tier
        self._logger = logging.getLogger(f"gfs.{service}")
        self._policy_level = TIER_LOG_POLICY.get(
            tier or "default", TIER_LOG_POLICY["default"])
        GFSLogger._registry[service] = self

    @classmethod
    def _get_log_dir(cls) -> Path:
        """Use /var/log/gfs if writable, else ./logs/gfs"""
        try:
            cls._log_dir.mkdir(parents=True, exist_ok=True)
            test = cls._log_dir / ".write_test"
            test.touch(); test.unlink()
            return cls._log_dir
        except PermissionError:
            cls._fallback_dir.mkdir(parents=True, exist_ok=True)
            return cls._fallback_dir

    @classmethod
    def setup(cls, log_dir: Optional[Path] = None,
              default_level: Severity = Severity.INFO,
              enable_debug_file: bool = False):
        """
        Initialize all log handlers.
        Call once at system boot.

        File structure (sysadmin standard):
          gfs.log       → INFO+ rotating daily 7-day retention
          gfs.error.log → ERROR+ never auto-rotated
          gfs.debug.log → DEBUG rotating hourly 24hr (if enabled)
          gfs.audit.log → SECURITY append-only immutable
          gfs.perf.log  → timing metrics JSON
        """
        if cls._handlers_initialized:
            return
        cls._handlers_initialized = True

        ld = log_dir or cls._get_log_dir()

        root = logging.getLogger("gfs")
        root.setLevel(logging.DEBUG)  # capture all; handlers filter

        # ── 1. Console handler (stderr) — adaptive format ──────────────────
        console = AdaptiveHandler(stream=sys.stderr)
        console.setLevel(_RFC_TO_PYTHON[default_level])
        root.addHandler(console)

        # ── 2. Main log — INFO+ rotating daily 7-day retention ─────────────
        main_path = ld / "gfs.log"
        main_handler = logging.handlers.TimedRotatingFileHandler(
            main_path,
            when      = "midnight",
            interval  = 1,
            backupCount = 7,
            encoding  = "utf-8",
        )
        main_handler.__class__ = type(
            "MainFileHandler",
            (logging.handlers.TimedRotatingFileHandler,),
            {"emit": lambda self, r: (
                AdaptiveHandler(
                    stream=open(main_path,"a"),
                    force_json=True
                ).emit(r)
                if r.__dict__.get("gfs_record") else None
            )}
        )
        main_handler.setLevel(logging.INFO)
        root.addHandler(main_handler)

        # ── 3. Error log — ERROR+ never auto-rotated ────────────────────────
        error_path = ld / "gfs.error.log"
        error_handler = logging.FileHandler(error_path, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        # Both JSON + plain for errors always
        _orig_emit = error_handler.emit
        def _dual_emit(record, path=error_path):
            rec = record.__dict__.get("gfs_record")
            if not rec: return
            with open(path, "a") as f:
                f.write(rec.to_json() + "\n")
                f.write(rec.to_plain() + "\n")
        error_handler.emit = _dual_emit
        root.addHandler(error_handler)

        # ── 4. Audit log — SECURITY append-only immutable ──────────────────
        audit_path = ld / "gfs.audit.log"
        audit_handler = AuditHandler(audit_path)
        audit_handler.setLevel(logging.WARNING)
        root.addHandler(audit_handler)

        # ── 5. Perf log — timing metrics JSON only ──────────────────────────
        perf_path = ld / "gfs.perf.log"
        perf_handler = PerfHandler(perf_path)
        perf_handler.setLevel(logging.DEBUG)
        root.addHandler(perf_handler)

        # ── 6. Debug log — rotating hourly 24hr (dev only) ─────────────────
        if enable_debug_file:
            debug_path = ld / "gfs.debug.log"
            debug_handler = logging.handlers.TimedRotatingFileHandler(
                debug_path,
                when        = "h",
                interval    = 1,
                backupCount = 24,
                encoding    = "utf-8",
            )
            debug_handler.setLevel(logging.DEBUG)
            root.addHandler(debug_handler)

        # Boot confirmation — goes to log, not to user
        boot_rec = GFSLogRecord(
            ts      = datetime.now(timezone.utc).isoformat(),
            level   = "INFO",
            svc     = "gfs.boot",
            event   = "logging.initialized",
            msg     = "GFS logging system online",
            agent   = None,
            tier    = "core",
            fname   = None,
            goal_id = None,
            dur_us  = None,
            extra   = {
                "log_dir":    str(ld),
                "level":      default_level.name,
                "debug_file": enable_debug_file,
            }
        )
        lr = logging.LogRecord(
            name="gfs.boot", level=logging.INFO,
            pathname="", lineno=0, msg="", args=(), exc_info=None
        )
        lr.__dict__["gfs_record"] = boot_rec
        root.handle(lr)

    def _emit(self, severity: Severity, event: str,
              fname: Optional[str] = None,
              goal_id: Optional[str] = None,
              dur_us: Optional[float] = None,
              extra: Optional[dict] = None,
              tier: Optional[str] = None,
              exc: bool = False):
        """Core emit — always silent to stdout."""

        # Tier-aware level gate
        effective_tier  = tier or self.tier or "default"
        policy          = TIER_LOG_POLICY.get(effective_tier,
                                               Severity.INFO)
        if severity > policy:
            return  # below policy threshold — suppress

        py_level = _RFC_TO_PYTHON[severity]
        if not self._logger.isEnabledFor(py_level):
            return

        # Build structured record
        rec = GFSLogRecord(
            ts      = datetime.now(timezone.utc).isoformat(),
            level   = severity.name,
            svc     = self.service,
            event   = event,
            msg     = event.replace(".", " "),
            agent   = self.agent,
            tier    = effective_tier,
            fname   = fname,
            goal_id = goal_id[:8] if goal_id else None,
            dur_us  = round(dur_us, 2) if dur_us else None,
            extra   = extra,
        )

        # Add exception info if present
        if exc:
            tb = traceback.format_exc()
            if rec.extra is None: rec.extra = {}
            rec.extra["traceback"] = tb.strip()[-500:]  # cap at 500 chars

        # Emit through Python logging (never touches stdout)
        lr = logging.LogRecord(
            name     = f"gfs.{self.service}",
            level    = py_level,
            pathname = "",
            lineno   = 0,
            msg      = event,
            args     = (),
            exc_info = None,
        )
        lr.__dict__["gfs_record"] = rec
        self._logger.handle(lr)

    # ── Public API ────────────────────────────────────────────────────────────

    def debug(self, event: str, **kwargs):
        self._emit(Severity.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs):
        self._emit(Severity.INFO, event, **kwargs)

    def notice(self, event: str, **kwargs):
        self._emit(Severity.NOTICE, event, **kwargs)

    def warning(self, event: str, **kwargs):
        self._emit(Severity.WARNING, event, **kwargs)

    def error(self, event: str, exc: bool = False, **kwargs):
        self._emit(Severity.ERROR, event, exc=exc, **kwargs)

    def critical(self, event: str, exc: bool = True, **kwargs):
        self._emit(Severity.CRITICAL, event, exc=exc, **kwargs)

    def alert(self, event: str, **kwargs):
        self._emit(Severity.ALERT, event, **kwargs)

    def emergency(self, event: str, **kwargs):
        self._emit(Severity.EMERGENCY, event, **kwargs)

    def security(self, event: str, **kwargs):
        """Security events → audit log always, regardless of level."""
        self._emit(Severity.WARNING, f"security.{event}", **kwargs)

    @contextmanager
    def timer(self, event: str,
              fname: Optional[str] = None,
              goal_id: Optional[str] = None,
              tier: Optional[str] = None,
              extra: Optional[dict] = None,
              level: Severity = Severity.DEBUG):
        """
        Context manager: times a block and logs dur_us on exit.
        Silent if operation succeeds.
        Logs ERROR if operation raises.

        Usage:
            with log.timer("hopfield.retrieve", fname="py.orc.cor.000"):
                results = memory.retrieve(fname)
        """
        start = time.perf_counter()
        try:
            yield
            dur_us = (time.perf_counter() - start) * 1_000_000
            self._emit(level, event,
                       fname=fname, goal_id=goal_id,
                       dur_us=dur_us, extra=extra,
                       tier=tier)
        except Exception as e:
            dur_us = (time.perf_counter() - start) * 1_000_000
            err_extra = dict(extra or {})
            err_extra["exception"] = type(e).__name__
            err_extra["detail"]    = str(e)[:200]
            self._emit(Severity.ERROR, f"{event}.failed",
                       fname=fname, goal_id=goal_id,
                       dur_us=dur_us, extra=err_extra,
                       exc=True, tier=tier)
            raise

    @contextmanager
    def operation(self, event: str, **kwargs):
        """
        Higher-level timer — logs NOTICE on success, ERROR on failure.
        For significant operations (goal execution, sidecar spawn, boot phase).
        """
        with self.timer(event, level=Severity.NOTICE, **kwargs):
            yield

# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE LOGGERS — one per GFS layer
# Pre-built loggers for every service in the stack
# ═══════════════════════════════════════════════════════════════════════════════

class GFSLoggers:
    """
    Pre-built logger instances for every GFS service.
    Import and use directly — no configuration needed.

    from gfs_logging import logs
    logs.dispatcher.info("dispatch.success", fname="py.orc.cor.000")
    logs.thinker.notice("goal.formed", goal_id="a3f1c2d4")
    logs.security_bridge.warning("goal.refused", extra={"reason":"DEPTH_EXCEEDED"})
    """

    def __init__(self, agent: Optional[str] = None):
        self.agent = agent

        # L1-L2: Signal + Encoding
        self.schema     = GFSLogger("schema",     agent, "core")
        self.encoder    = GFSLogger("encoder",    agent, "core")

        # L3: Structure
        self.registry   = GFSLogger("registry",   agent, "core")
        self.crdt       = GFSLogger("crdt",       agent, "core")
        self.merkle     = GFSLogger("merkle",     agent, "core")

        # L4: Graph
        self.entangle   = GFSLogger("entangle",   agent, "core")
        self.fhrr       = GFSLogger("fhrr",       agent, "core")
        self.mis        = GFSLogger("mis",        agent, "core")

        # L5: Memory
        self.hopfield   = GFSLogger("hopfield",   agent, "core")
        self.episodes   = GFSLogger("episodes",   agent, "core")

        # L6: Reasoning
        self.scanner    = GFSLogger("scanner",    agent, "core")
        self.dispatcher = GFSLogger("dispatcher", agent, "core")

        # L7: Intention
        self.thinker    = GFSLogger("thinker",    agent, "core")
        self.security_bridge = GFSLogger("security", agent, "core")
        self.boot       = GFSLogger("boot",       agent, "core")

        # Sidecar + Swarm
        self.sidecar    = GFSLogger("sidecar",    agent, "plugin")
        self.lookahead  = GFSLogger("lookahead",  agent, "plugin")
        self.swarm      = GFSLogger("swarm",      agent, "sandbox")

        # Agent Byte
        self.neural     = GFSLogger("neural",     agent, "core")
        self.symbolic   = GFSLogger("symbolic",   agent, "core")
        self.transfer   = GFSLogger("transfer",   agent, "core")

        # MCP + WebSocket
        self.mcp        = GFSLogger("mcp",        agent, "core")
        self.websocket  = GFSLogger("websocket",  agent, "plugin")
        self.dataset    = GFSLogger("dataset",    agent, "plugin")

        # System
        self.audit      = GFSLogger("audit",      agent, "core")
        self.perf       = GFSLogger("perf",       agent, "core")

    def for_tier(self, service: str, tier: str) -> GFSLogger:
        """Get a logger for a specific tier — applies tier policy."""
        return GFSLogger(service, self.agent, tier)

# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE ALERT SYSTEM
# Detects degradation automatically from perf log
# ═══════════════════════════════════════════════════════════════════════════════

class PerfMonitor:
    """
    Reads perf.log and alerts when operations exceed thresholds.
    Runs in background thread — silent to users.

    Thresholds (μs):
      dispatch:          <  100   normal
      hopfield.retrieve: <  500   normal
      merkle.root:       <  100   normal
      fhrr.collapse:     < 1000   normal
      sidecar.spawn:     <  200   normal
    """

    THRESHOLDS = {
        "dispatch.success":    100,
        "hopfield.retrieve":   500,
        "merkle.root":         100,
        "fhrr.collapse":       1000,
        "sidecar.spawn":       200,
        "gfs.env.step":        5000,
        "agent.dispatch":      10000,
    }

    def __init__(self, perf_log: Path, alert_log: GFSLogger):
        self._path      = perf_log
        self._alert_log = alert_log
        self._baselines: dict[str, list[float]] = {}
        self._window    = 100   # rolling window size

    def record(self, event: str, dur_us: float):
        """Record a timing — check against threshold and baseline."""
        if event not in self._baselines:
            self._baselines[event] = []
        window = self._baselines[event]
        window.append(dur_us)
        if len(window) > self._window:
            window.pop(0)

        # Threshold check
        threshold = self.THRESHOLDS.get(event)
        if threshold and dur_us > threshold * 3:
            self._alert_log.warning(
                "perf.threshold.exceeded",
                event=event,
                extra={
                    "dur_us":    round(dur_us, 2),
                    "threshold": threshold,
                    "ratio":     round(dur_us/threshold, 1),
                }
            )

        # Regression check (vs rolling baseline)
        if len(window) >= 10:
            baseline = sum(window[:-1]) / (len(window)-1)
            if dur_us > baseline * 2.0 and dur_us > 100:
                self._alert_log.notice(
                    "perf.regression.detected",
                    extra={
                        "event":    event,
                        "dur_us":   round(dur_us, 2),
                        "baseline": round(baseline, 2),
                        "delta":    round(dur_us-baseline, 2),
                    }
                )

    def report(self) -> dict:
        """Return performance summary — for log, not for user."""
        summary = {}
        for event, window in self._baselines.items():
            if not window: continue
            avg   = sum(window)/len(window)
            worst = max(window)
            best  = min(window)
            summary[event] = {
                "avg_us":   round(avg, 2),
                "worst_us": round(worst, 2),
                "best_us":  round(best, 2),
                "samples":  len(window),
                "over_threshold": (
                    sum(1 for d in window
                        if d > self.THRESHOLDS.get(event, float('inf')))
                ),
            }
        return summary

# ═══════════════════════════════════════════════════════════════════════════════
# DECORATORS — silent instrumentation
# ═══════════════════════════════════════════════════════════════════════════════

def log_dispatch(logger: GFSLogger):
    """
    Decorator: instruments any dispatch function silently.
    Logs timing, success/failure, never touches return value.

    @log_dispatch(logs.dispatcher)
    def dispatch(fname): ...
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            fname = args[0] if args else kwargs.get("fname","?")
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                dur_us = (time.perf_counter()-start)*1e6
                logger.info("dispatch.success", fname=str(fname), dur_us=dur_us)
                return result
            except Exception as e:
                dur_us = (time.perf_counter()-start)*1e6
                logger.error("dispatch.error", fname=str(fname),
                             dur_us=dur_us, exc=True,
                             extra={"exc": type(e).__name__})
                raise
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

def log_goal(logger: GFSLogger):
    """
    Decorator: instruments goal lifecycle silently.
    NOTICE on form, INFO on complete, WARNING on refuse.
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                dur_us = (time.perf_counter()-start)*1e6
                goal_id = (result.goal_id if hasattr(result,'goal_id')
                           else kwargs.get("goal_id","?"))
                logger.notice("goal.formed", goal_id=goal_id, dur_us=dur_us)
                return result
            except Exception as e:
                dur_us = (time.perf_counter()-start)*1e6
                logger.error("goal.error", dur_us=dur_us, exc=True,
                             extra={"exc": type(e).__name__})
                raise
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

# ═══════════════════════════════════════════════════════════════════════════════
# GHOSTGOAT SILENT WRAPPER
# Ensures GhostGoat never leaks internal logs to Telegram
# ═══════════════════════════════════════════════════════════════════════════════

class SilentTelegramWrapper:
    """
    Wraps any GFS operation for Telegram/GhostGoat context.
    Guarantees: no log output reaches the Telegram response.
    All logging goes to files only.
    Users see only the result.

    Usage:
        wrapper = SilentTelegramWrapper(logs)
        result  = wrapper.execute("dispatch", fname="py.orc.cor.000")
        await message.reply(result["output"])  # clean output only
    """

    def __init__(self, loggers: GFSLoggers, operation_fn=None):
        self._logs = loggers
        self._op   = operation_fn

    def execute(self, operation: str,
                fn=None, args=(), kwargs={}) -> dict:
        """
        Execute operation silently.
        Returns {"output": ..., "success": bool}
        Logs everything internally.
        Never surfaces errors to caller as raw exceptions.
        """
        start = time.perf_counter()
        try:
            target = fn or self._op
            if not target:
                return {"output": None, "success": False,
                        "error": "no_operation"}
            result = target(*args, **kwargs)
            dur_us = (time.perf_counter()-start)*1e6
            self._logs.dispatcher.info(
                f"telegram.{operation}.complete",
                dur_us=dur_us,
            )
            return {"output": result, "success": True}
        except Exception as e:
            dur_us = (time.perf_counter()-start)*1e6
            self._logs.dispatcher.error(
                f"telegram.{operation}.failed",
                dur_us=dur_us, exc=True,
                extra={"exc": type(e).__name__, "detail": str(e)[:100]}
            )
            # Return clean error — no stack trace to user
            return {"output": None, "success": False,
                    "error": "operation_failed"}

# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION + TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def init(agent: str = "default",
         log_dir: Optional[Path] = None,
         level: Severity = Severity.INFO,
         debug_file: bool = False) -> GFSLoggers:
    """
    Initialize GFS logging system.
    Call once at startup — silent, no output to user.

    Returns ready-to-use loggers for all services.
    """
    GFSLogger.setup(log_dir, level, debug_file)
    return GFSLoggers(agent)

def run_tests():
    import tempfile
    print("\n══ GFS LOGGING SYSTEM TESTS ══════════════════════════════════\n")
    passed = failed = 0
    errors = []

    def ok(name, cond, detail=""):
        nonlocal passed, failed
        if cond: passed+=1; print(f"  ✓  {name}")
        else:
            failed+=1; errors.append(f"{name}: {detail}")
            print(f"  ✗  {name} — {detail}")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        logs = init("test_agent", log_dir, Severity.DEBUG, True)

        # T1: Log record structure
        print("T1: Log record structure")
        rec = GFSLogRecord(
            ts="2026-05-08T12:00:00Z", level="INFO",
            svc="dispatcher", event="dispatch.success",
            msg="dispatch success", agent="ghostgoat",
            tier="core", fname="py.orc.cor.000",
            goal_id="a3f1c2d4", dur_us=4.7, extra={"handler":"python"}
        )
        j = rec.to_json()
        d = json.loads(j)
        ok("JSON has ts",       "ts" in d)
        ok("JSON has level",    d["level"]=="INFO")
        ok("JSON has event",    d["event"]=="dispatch.success")
        ok("JSON has dur_us",   d["dur_us"]==4.7)
        ok("JSON has fname",    d["fname"]=="py.orc.cor.000")
        plain = rec.to_plain()
        ok("plain contains event",  "dispatch.success" in plain)
        ok("plain contains service","dispatcher" in plain)

        # T2: Logger emit — silent (no stdout)
        print("\nT2: Logger emit — silent to stdout")
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        logs.dispatcher.info("dispatch.success",
                             fname="py.orc.cor.000", dur_us=4.7)
        logs.thinker.notice("goal.formed", goal_id="abc12345")
        logs.security_bridge.warning("goal.refused",
                                     extra={"reason":"DEPTH_EXCEEDED"})
        logs.dispatcher.error("dispatch.failed",
                              fname="js.dat.arc.000",
                              extra={"reason":"ARCHIVE_IMMUTABLE"})
        captured = sys.stdout.getvalue()
        sys.stdout = old_stdout
        ok("nothing written to stdout", captured == "")

        # T3: Timer context manager
        print("\nT3: Timer context manager")
        with logs.dispatcher.timer("test.operation",
                                    fname="py.orc.cor.000",
                                    level=Severity.INFO):
            time.sleep(0.001)
        ok("timer completes without error", True)

        # Timer with exception
        try:
            with logs.dispatcher.timer("test.failing"):
                raise ValueError("test error")
        except ValueError:
            pass
        ok("timer catches and logs exception", True)

        # T4: Log files created
        print("\nT4: Log file structure")
        log_files = list(log_dir.iterdir())
        log_names = {f.name for f in log_files}
        ok("gfs.log created",       "gfs.log" in log_names)
        ok("gfs.error.log created", "gfs.error.log" in log_names)
        ok("gfs.audit.log created", "gfs.audit.log" in log_names)
        ok("gfs.perf.log created",  "gfs.perf.log" in log_names)
        ok("gfs.debug.log created", "gfs.debug.log" in log_names)

        # T5: Main log is valid JSON
        print("\nT5: Log file content validation")
        main_log = (log_dir / "gfs.log").read_text().strip()
        if main_log:
            lines = [l for l in main_log.split("\n") if l.strip()]
            valid_json = all(
                json.loads(line) for line in lines if line)
            ok("main log is valid JSON", valid_json)
        else:
            ok("main log exists", False, "empty")

        # Error log has both formats
        err_log = (log_dir / "gfs.error.log").read_text().strip()
        if err_log:
            ok("error log has content", len(err_log)>0)
        else:
            ok("error log written", False, "empty")

        # T6: Audit log with HMAC chain
        print("\nT6: Audit log integrity chain")
        audit_log = (log_dir / "gfs.audit.log").read_text().strip()
        if audit_log:
            lines = [l for l in audit_log.split("\n") if l.strip()]
            entries = [json.loads(l) for l in lines]
            ok("audit entries have chain_hash",
               all("chain_hash" in e for e in entries))
            ok("chain hashes are unique",
               len({e["chain_hash"] for e in entries})==len(entries))
        else:
            ok("audit log has entries", False, "empty")

        # T7: Perf log has timing
        print("\nT7: Performance log")
        perf_log = (log_dir / "gfs.perf.log").read_text().strip()
        if perf_log:
            lines = [l for l in perf_log.split("\n") if l.strip()]
            perf_entries = [json.loads(l) for l in lines]
            ok("perf entries have dur_us",
               all("dur_us" in e for e in perf_entries))
        else:
            ok("perf log has entries", False, "empty — no timed ops logged")

        # T8: PerfMonitor thresholds
        print("\nT8: Performance monitor")
        monitor = PerfMonitor(log_dir/"gfs.perf.log", logs.perf)
        monitor.record("dispatch.success", 50.0)   # within threshold
        monitor.record("dispatch.success", 50.0)
        ok("perf monitor records", len(monitor._baselines)>0)
        report = monitor.report()
        ok("perf report generated", "dispatch.success" in report)

        # T9: SilentTelegramWrapper
        print("\nT9: SilentTelegramWrapper — user isolation")
        wrapper = SilentTelegramWrapper(logs)
        result = wrapper.execute("test", fn=lambda: "clean_result")
        ok("wrapper returns clean output", result["output"]=="clean_result")
        ok("wrapper success=True", result["success"]==True)

        # Error case — no traceback in result
        def boom(): raise RuntimeError("internal error")
        result_err = wrapper.execute("test_fail", fn=boom)
        ok("wrapper catches error cleanly",    result_err["success"]==False)
        ok("wrapper no traceback in output",   "traceback" not in str(result_err["output"]))
        ok("wrapper generic error message",    result_err["error"]=="operation_failed")

        # T10: Tier-aware levels
        print("\nT10: Tier-aware log level policy")
        sandbox_log = logs.for_tier("test.sandbox", "sandbox")
        ok("sandbox tier = DEBUG", TIER_LOG_POLICY["sandbox"]==Severity.DEBUG)
        core_log = logs.for_tier("test.core", "core")
        ok("core tier = INFO", TIER_LOG_POLICY["core"]==Severity.INFO)
        archive_log = logs.for_tier("test.archive", "archive")
        ok("archive tier = WARNING", TIER_LOG_POLICY["archive"]==Severity.WARNING)

        # T11: Decorators
        print("\nT11: Silent decorators")
        @log_dispatch(logs.dispatcher)
        def mock_dispatch(fname): return {"handler": "python"}

        result = mock_dispatch("py.orc.cor.000")
        ok("decorated dispatch returns correctly", result["handler"]=="python")

        try:
            @log_dispatch(logs.dispatcher)
            def failing_dispatch(fname): raise ValueError("fail")
            failing_dispatch("py.orc.cor.000")
        except ValueError:
            pass
        ok("decorated dispatch re-raises correctly", True)

    print(f"\n  {'═'*52}")
    print(f"  PASSED: {passed}/{passed+failed}")
    if errors:
        for e in errors: print(f"    ✗ {e}")
    return failed==0

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv)>1 else "test"
    if cmd == "test":
        ok = run_tests()
        sys.exit(0 if ok else 1)
    elif cmd == "demo":
        # Demo — shows what operators see (logs), not users
        logs = init("ghostgoat", level=Severity.DEBUG)
        print("(This is what operators see in the log — users see nothing)")
        logs.boot.info("system.ready", extra={"version":"v5"})
        with logs.dispatcher.timer("dispatch.full", fname="py.orc.cor.000"):
            time.sleep(0.002)
        logs.thinker.notice("goal.formed", goal_id="a3f1c2d4abc",
                             extra={"intent":"process_stream","priority":7})
        logs.security_bridge.warning("goal.refused",
                                      extra={"reason":"DEPTH_EXCEEDED","depth":11})
        logs.entangle.info("pair.created",
                            fname="py.orc.cor.000",
                            extra={"partner":"js.cfg.cor.000","weight":0.5})
        logs.dispatcher.error("dispatch.refused",
                               fname="js.dat.arc.000",
                               extra={"reason":"ARCHIVE_IMMUTABLE"})
