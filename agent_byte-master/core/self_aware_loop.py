"""
Self-Aware Loop — Wires self-healing, self-optimizing, and self-monitoring
into a single active feedback loop.

This is the "nervous system" that connects:
  - NeuroGraph.self_heal()         → graph integrity repair
  - Diagnostics (self_check)       → filesystem / dep / registry checks
  - SelfModifyingDiagnostics (ASI) → system metrics + adaptive thresholds
  - Optimizer                      → performance tracking + suggestions
  - MonitoringSystem               → metrics collection + health checks

Architecture:
  SelfAwareLoop runs a background async loop that periodically:
    1. Collects system health from all subsystems
    2. Detects anomalies (resource, graph, component failures)
    3. Executes self-healing actions when thresholds are crossed
    4. Records performance observations for the optimizer
    5. Adapts its own check intervals based on system stability
"""

import asyncio
import gc
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
# init_dual_brain removed — wire orchestrator at startup

# At startup
# dual_brain wired at startup

logger = logging.getLogger(__name__)


class SelfAwareLoop:
    """Active feedback loop that makes GhostGoat self-healing and self-optimizing."""

    def __init__(self, core_integration):
        """
        Args:
            core_integration: A CoreIntegration instance (from core/core_integration.py).
                              Subsystems are accessed lazily through it.
        """
        self.core = core_integration
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Adaptive interval: starts at 30s, shortens under stress, lengthens when stable
        self.check_interval = 30.0
        self._min_interval = 10.0
        self._max_interval = 120.0

        # Health history for trend detection
        self.health_history: List[Dict[str, Any]] = []
        self._max_history = 500

        # Counters
        self.heals_performed = 0
        self.optimizations_run = 0
        self.cycles_completed = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the self-aware loop in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.info("SelfAwareLoop already running")
            return

        self.running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ghostgoat-self-aware"
        )
        self._thread.start()
        logger.info("SelfAwareLoop started (interval=%.1fs)", self.check_interval)

    def stop(self):
        """Signal the loop to stop."""
        self.running = False
        logger.info("SelfAwareLoop stop requested")

    def _run_loop(self):
        """Thread entry — creates an event loop and runs the async cycle."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_loop())
        except Exception as e:
            logger.error("SelfAwareLoop crashed: %s", e)
        finally:
            self._loop.close()

    async def _async_loop(self):
        """Main async loop — runs until stopped."""
        while self.running:
            try:
                snapshot = await self._collect_health()
                anomalies = self._detect_anomalies(snapshot)

                if anomalies:
                    await self._self_heal(anomalies, snapshot)

                self._record_snapshot(snapshot, anomalies)
                self._adapt_interval(snapshot, anomalies)
                self.cycles_completed += 1

            except Exception as e:
                logger.error("SelfAwareLoop cycle error: %s", e)

            await asyncio.sleep(self.check_interval)

    # ------------------------------------------------------------------
    # 1. Collect health from all subsystems
    # ------------------------------------------------------------------

    async def _collect_health(self) -> Dict[str, Any]:
        """Gather health signals from every reachable subsystem."""
        snapshot: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "neurograph": None,
            "diagnostics": None,
            "optimizer": None,
            "monitoring": None,
            "asi": None,
            "memory_py": None,
        }

        # NeuroGraph health
        try:
            ng = self.core.neurograph
            if ng:
                snapshot["neurograph"] = ng.health_check()
        except Exception as e:
            snapshot["neurograph"] = {"ok": False, "error": str(e)}

        # Diagnostics (filesystem / deps)
        try:
            diag = self.core.diagnostics
            if diag and "run_all" in diag:
                snapshot["diagnostics"] = diag["run_all"](auto_fix=True, auto_install=False)
        except Exception as e:
            snapshot["diagnostics"] = {"error": str(e)}

        # ASI self-modifying diagnostics (system metrics)
        try:
            asi = self.core.asi
            if asi and hasattr(asi, "collect_system_metrics"):
                snapshot["asi"] = asi.collect_system_metrics()
        except Exception as e:
            snapshot["asi"] = {"error": str(e)}

        # Monitoring system
        try:
            from frameworks.monitoring.monitoring import get_monitoring
            mon = get_monitoring()
            snapshot["monitoring"] = mon.get_dashboard_data()
        except Exception as e:
            snapshot["monitoring"] = {"error": str(e)}

        # Python memory stats
        import sys
        snapshot["memory_py"] = {
            "gc_counts": gc.get_count(),
            "gc_threshold": gc.get_threshold(),
            "objects_tracked": len(gc.get_objects()) if len(gc.get_objects()) < 50000 else "50000+",
        }

        return snapshot

    # ------------------------------------------------------------------
    # 2. Detect anomalies
    # ------------------------------------------------------------------

    def _detect_anomalies(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze snapshot for problems that need healing."""
        anomalies = []

        # Neurograph issues
        ng = snapshot.get("neurograph")
        if ng and isinstance(ng, dict):
            if not ng.get("ok", True):
                anomalies.append({
                    "source": "neurograph",
                    "severity": "medium",
                    "type": "graph_unhealthy",
                    "detail": ng.get("reason", "unknown"),
                })
            isolates = ng.get("isolates", [])
            if len(isolates) > 10:
                anomalies.append({
                    "source": "neurograph",
                    "severity": "low",
                    "type": "many_isolates",
                    "detail": f"{len(isolates)} isolated nodes",
                })

        # Diagnostics issues
        diag = snapshot.get("diagnostics")
        if diag and isinstance(diag, dict):
            missing = diag.get("missing_required_files", [])
            if missing:
                anomalies.append({
                    "source": "diagnostics",
                    "severity": "high",
                    "type": "missing_files",
                    "detail": missing,
                })

        # ASI system metrics
        asi = snapshot.get("asi")
        if asi and isinstance(asi, dict) and "memory" in asi:
            mem = asi.get("memory", {})
            virt = mem.get("virtual", {})
            mem_pct = virt.get("percent", 0)
            if mem_pct > 85:
                anomalies.append({
                    "source": "asi",
                    "severity": "critical",
                    "type": "memory_critical",
                    "detail": f"Memory at {mem_pct}%",
                })
            elif mem_pct > 70:
                anomalies.append({
                    "source": "asi",
                    "severity": "medium",
                    "type": "memory_warning",
                    "detail": f"Memory at {mem_pct}%",
                })

        # Python GC pressure
        gc_counts = snapshot.get("memory_py", {}).get("gc_counts", (0, 0, 0))
        if isinstance(gc_counts, tuple) and gc_counts[0] > 700:
            anomalies.append({
                "source": "python_gc",
                "severity": "low",
                "type": "gc_pressure",
                "detail": f"Gen0 count: {gc_counts[0]}",
            })

        return anomalies

    # ------------------------------------------------------------------
    # 3. Self-heal
    # ------------------------------------------------------------------

    async def _self_heal(self, anomalies: List[Dict], snapshot: Dict):
        """Execute healing actions based on detected anomalies."""
        for anomaly in anomalies:
            atype = anomaly["type"]
            severity = anomaly["severity"]
            logger.warning("SelfAwareLoop anomaly [%s] %s: %s",
                           severity, atype, anomaly.get("detail", ""))

            try:
                if atype == "graph_unhealthy":
                    ng = self.core.neurograph
                    if ng and hasattr(ng, "self_heal"):
                        ng.self_heal()
                        self.heals_performed += 1
                        logger.info("NeuroGraph self-heal executed")

                elif atype == "many_isolates":
                    ng = self.core.neurograph
                    if ng and hasattr(ng, "self_heal"):
                        ng.self_heal()
                        self.heals_performed += 1

                elif atype == "memory_critical":
                    gc.collect()
                    self.heals_performed += 1
                    logger.info("Emergency GC collect triggered")
                    # Also try ASI memory optimization
                    asi = self.core.asi
                    if asi and hasattr(asi, "optimize_memory"):
                        asi.optimize_memory()
                        logger.info("ASI memory optimization executed")

                elif atype == "gc_pressure":
                    gc.collect()
                    self.heals_performed += 1

                elif atype == "missing_files":
                    # Diagnostics auto_fix=True already tried to fix in collection
                    logger.info("Missing files detected — diagnostics auto-fix attempted")

                # Record observation in optimizer
                self.core.observe_performance(
                    "self_aware_loop",
                    f"heal:{atype}",
                    f"severity={severity}",
                )
                self.optimizations_run += 1

            except Exception as e:
                logger.error("Self-heal action failed for %s: %s", atype, e)

    # ------------------------------------------------------------------
    # 4. Record & adapt
    # ------------------------------------------------------------------

    def _record_snapshot(self, snapshot: Dict, anomalies: List[Dict]):
        """Store snapshot in history for trend analysis."""
        record = {
            "timestamp": snapshot["timestamp"],
            "anomaly_count": len(anomalies),
            "anomaly_types": [a["type"] for a in anomalies],
            "cycle": self.cycles_completed,
        }
        self.health_history.append(record)
        if len(self.health_history) > self._max_history:
            self.health_history = self.health_history[-self._max_history:]

    def _adapt_interval(self, snapshot: Dict, anomalies: List[Dict]):
        """Adjust check interval: faster when issues detected, slower when stable."""
        if anomalies:
            critical = any(a["severity"] == "critical" for a in anomalies)
            if critical:
                self.check_interval = self._min_interval
            else:
                self.check_interval = max(self._min_interval, self.check_interval * 0.8)
        else:
            self.check_interval = min(self._max_interval, self.check_interval * 1.1)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return loop status for dashboards / health checks."""
        return {
            "running": self.running,
            "cycles_completed": self.cycles_completed,
            "heals_performed": self.heals_performed,
            "optimizations_run": self.optimizations_run,
            "current_interval_s": round(self.check_interval, 1),
            "history_size": len(self.health_history),
            "recent_anomalies": (
                self.health_history[-1].get("anomaly_types", [])
                if self.health_history else []
            ),
        }
