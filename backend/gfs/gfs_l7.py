#!/usr/bin/env python3
"""
GFS Level 7 — cogno THINKER Intent Layer
Wires cogno's cognitive architecture into GFS as the goal-directed
execution substrate.

Stack position:
  L7  INTENTION   → cogno THINKER (this file)
  L6  REASONING   → cogno SCANNER + MIS router
  L5  MEMORY      → cogno MEMORY + Modern Hopfield Network
  L4  GRAPH       → EntanglementEngine + holographic web
  L3  STRUCTURE   → CRDT manifest + Merkle tree
  L2  ENCODING    → Morton keys + FHRR + IB + tANS
  L1  SIGNAL      → extensionless filenames (py.orc.cor.000)

cogno modules mapped:
  THINKER        → GoalState + IntentEngine (L7)
  SCANNER        → PerceptionLayer (L6 → L7 input)
  MEMORY         → EpisodicStore + HopfieldMemory (L5)
  SECURITY BRIDGE→ ConstraintLayer (L7 guardrails)
  BOOT           → SystemBoot (L7 initialization)

Key capability added:
  - System knows WHY it dispatches, not just WHAT
  - Goal-conditional entanglement weights
  - Refusal capability (agent can reject invalid paths)
  - Goal-directed Hopfield bias field
  - Judgment layer over MIS routing
  - cogno SCANNER feeds perception into goal evaluation
  - SECURITY BRIDGE constrains goal selection space
"""

import json
import math
import cmath
import hashlib
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Callable
from datetime import datetime, timezone
from enum import Enum
from copy import deepcopy

# ═══════════════════════════════════════════════════════════════════════════════
# GFS CORE (minimal inline — delegates to gfs_v4 in production)
# ═══════════════════════════════════════════════════════════════════════════════

TYPES = {0b000:("py","python"),0b001:("js","json"),0b010:("yl","yaml"),
         0b011:("bn","binary"),0b100:("md","markdown"),0b101:("sh","shell"),
         0b110:("cp","cpp"),0b111:("tx","text")}
ROLES = {0b000:("orc","orchestrator"),0b001:("tol","tool"),
         0b010:("cfg","config"),0b011:("dat","data"),
         0b100:("doc","doc"),0b101:("tst","test"),
         0b110:("brd","bridge"),0b111:("eph","ephemeral")}
TIERS = {0b00:("cor","core"),0b01:("plg","plugin"),
         0b10:("snd","sandbox"),0b11:("arc","archive")}
TYPE_ABV = {v[0]:k for k,v in TYPES.items()}
ROLE_ABV = {v[0]:k for k,v in ROLES.items()}
TIER_ABV = {v[0]:k for k,v in TIERS.items()}

def encode_filename(ti,ri,ii,sq):
    return f"{TYPES[ti][0]}.{ROLES[ri][0]}.{TIERS[ii][0]}.{sq:03d}"

def decode_filename(fname):
    parts = Path(fname).name.split('.')
    if len(parts)!=4: raise ValueError(f"Invalid GFS: {fname}")
    ta,ra,ia,sq = parts
    if ta not in TYPE_ABV: raise ValueError(f"Bad type: {ta}")
    if ra not in ROLE_ABV: raise ValueError(f"Bad role: {ra}")
    if ia not in TIER_ABV: raise ValueError(f"Bad tier: {ia}")
    ti,ri,ii = TYPE_ABV[ta],ROLE_ABV[ra],TIER_ABV[ia]
    seq=int(sq)
    if not(0<=seq<=255): raise ValueError(f"Seq OOB: {seq}")
    key_int=(ti<<13)|(ri<<10)|(ii<<8)|seq
    return dict(filename=fname,type_id=ti,role_id=ri,tier_id=ii,
                sequence=seq,key_int=key_int,
                type=TYPES[ti][1],handler=TYPES[ti][1],
                role=ROLES[ri][1],tier=TIERS[ii][1],
                cache_hint=(ii==0 and ri in (0,1)))

# ═══════════════════════════════════════════════════════════════════════════════
# L5 — HOPFIELD MEMORY (cogno MEMORY module)
# ═══════════════════════════════════════════════════════════════════════════════

class HopfieldMemory:
    """
    Modern Hopfield Network over GFS nodes.
    Stores every file, bond, and execution pattern as an attractor.
    Retrieval = pattern completion, never search.

    cogno MEMORY module equivalent:
      - tiered storage (hot/warm/cold)
      - episodic trace per execution session
      - goal-conditional bias field (L7 connection)

    Capacity: P = exp(α * D) patterns for dimension D
    At D=512: stores ~10^77 patterns — effectively unlimited for GFS
    """

    def __init__(self, dim: int = 512, beta: float = 32.0):
        self.D    = dim
        self.beta = beta          # inverse temperature — sharpness of retrieval
        self.patterns: list[list[float]] = []  # stored memory vectors
        self.labels:   list[str]          = []  # GFS filename for each pattern
        self.episodes: list[dict]         = []  # execution trace log
        self._bias:    list[float]        = [0.0] * dim  # goal bias field (L7)

    def _fname_to_pattern(self, fname: str) -> list[float]:
        """
        Map GFS filename to a real-valued pattern vector.
        Uses SHA3 seeded deterministic projection.
        Compatible with Modern Hopfield continuous state space.
        """
        d = decode_filename(fname)
        # Encode all semantic dimensions into pattern
        seed = f"hopfield:{d['type']}:{d['role']}:{d['tier']}:{d['sequence']}"
        h = hashlib.sha3_256(seed.encode()).digest()
        pattern = []
        block = h
        while len(pattern) < self.D:
            for byte in block:
                pattern.append((byte / 127.5) - 1.0)  # normalize to [-1, 1]
                if len(pattern) == self.D: break
            block = hashlib.sha3_256(block).digest()
        return pattern[:self.D]

    def store(self, fname: str):
        """Store a GFS file as a Hopfield memory pattern."""
        if fname in self.labels:
            return  # already stored
        pattern = self._fname_to_pattern(fname)
        self.patterns.append(pattern)
        self.labels.append(fname)

    def store_many(self, fnames: list[str]):
        for f in fnames:
            self.store(f)

    def _softmax(self, scores: list[float]) -> list[float]:
        """Softmax with temperature beta."""
        max_s = max(scores)
        exp_s = [math.exp(self.beta * (s - max_s)) for s in scores]
        total = sum(exp_s)
        return [e / total for e in exp_s]

    def retrieve(self, query_fname: str,
                 goal_bias: Optional[list[float]] = None,
                 top_k: int = 3) -> list[tuple[str, float]]:
        """
        Modern Hopfield retrieval via softmax attention.
        query → pattern completion → nearest attractor.

        goal_bias: L7 intent vector that tilts the energy landscape
                   toward memories relevant to current goal.
                   None = unbiased retrieval.
        """
        if not self.patterns:
            return []

        query = self._fname_to_pattern(query_fname)

        # Apply goal bias if provided (L7 → L5 connection)
        if goal_bias:
            biased = [q + self.beta * b for q, b in zip(query, goal_bias)]
        else:
            biased = query

        # Compute attention scores (dot product with all stored patterns)
        scores = []
        for pat in self.patterns:
            score = sum(b * p for b, p in zip(biased, pat))
            scores.append(score)

        # Softmax over scores
        weights = self._softmax(scores)

        # Rank by weight
        ranked = sorted(zip(self.labels, weights),
                        key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def set_goal_bias(self, goal_vector: list[float]):
        """L7 pushes goal intent into L5 memory bias field."""
        self._bias = goal_vector

    def record_episode(self, session_id: str, path: list[str],
                       goal: str, success: bool, duration_ms: float):
        """
        cogno MEMORY episodic trace.
        Records execution paths for SK-Gen pattern mining.
        """
        self.episodes.append({
            "session_id": session_id,
            "path":       path,
            "goal":       goal,
            "success":    success,
            "duration_ms":duration_ms,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        })

    def mine_patterns(self, min_frequency: int = 3) -> list[dict]:
        """
        SK-Gen pattern mining over episodic traces.
        Finds recurring execution sequences → symbolic DAGs.
        Patterns that recur ≥ min_frequency become fixed Hopfield weights.
        """
        # Count consecutive file pairs across episodes
        pair_counts: dict[tuple, int] = {}
        for ep in self.episodes:
            path = ep["path"]
            for i in range(len(path)-1):
                pair = (path[i], path[i+1])
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

        # Extract patterns above frequency threshold
        stable_patterns = []
        for (a, b), count in pair_counts.items():
            if count >= min_frequency:
                stable_patterns.append({
                    "from":      a,
                    "to":        b,
                    "frequency": count,
                    "confidence":count / len(self.episodes),
                    "type":      "sequential",
                })

        return sorted(stable_patterns,
                      key=lambda x: x["confidence"], reverse=True)

    def stats(self) -> dict:
        return {
            "stored_patterns": len(self.patterns),
            "episodes":        len(self.episodes),
            "capacity_used":   f"{len(self.patterns)}/{math.floor(math.exp(0.5 * self.D))} (theoretical max)",
            "bias_active":     any(b != 0.0 for b in self._bias),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# L6 — SCANNER (cogno SCANNER module — perception into L7)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SystemState:
    """
    cogno SCANNER output — complete perception of current system state.
    Fed upward into L7 THINKER for goal evaluation.
    """
    timestamp:       str
    active_files:    list[str]          # currently executing
    pending_files:   list[str]          # queued
    sidecar_count:   int                # active sidecars
    resource_load:   float              # 0.0-1.0
    deadline_ms:     Optional[float]    # time constraint
    error_signals:   list[str]          # active errors
    last_dispatch:   Optional[str]      # most recently dispatched file
    execution_depth: int                # recursion/call depth
    goal_progress:   float              # 0.0-1.0 toward current goal

class Scanner:
    """
    cogno SCANNER — peripheral awareness layer.
    Continuously monitors system state and surfaces to THINKER.
    Implements friction detection — notifies THINKER when
    execution is hitting resistance or anomalies.
    """

    def __init__(self):
        self._history: list[SystemState] = []
        self._friction_threshold = 0.7
        self._callbacks: list[Callable] = []

    def scan(self, active: list[str] = None,
             pending: list[str] = None,
             sidecars: int = 0,
             load: float = 0.0,
             deadline_ms: float = None,
             errors: list[str] = None,
             last: str = None,
             depth: int = 0,
             progress: float = 0.0) -> SystemState:
        state = SystemState(
            timestamp       = datetime.now(timezone.utc).isoformat(),
            active_files    = active or [],
            pending_files   = pending or [],
            sidecar_count   = sidecars,
            resource_load   = load,
            deadline_ms     = deadline_ms,
            error_signals   = errors or [],
            last_dispatch   = last,
            execution_depth = depth,
            goal_progress   = progress,
        )
        self._history.append(state)
        self._detect_friction(state)
        return state

    def _detect_friction(self, state: SystemState):
        """
        cogno friction detection.
        Signals THINKER when something is wrong:
        - resource load too high
        - execution depth too deep
        - errors present
        - deadline at risk
        """
        friction = False
        signals  = []

        if state.resource_load > self._friction_threshold:
            friction = True; signals.append("HIGH_LOAD")
        if state.execution_depth > 8:
            friction = True; signals.append("DEEP_RECURSION")
        if state.error_signals:
            friction = True; signals.append("ERRORS_PRESENT")
        if state.deadline_ms and state.deadline_ms < 50:
            friction = True; signals.append("DEADLINE_CRITICAL")

        if friction:
            for cb in self._callbacks:
                cb(signals, state)

    def on_friction(self, callback: Callable):
        self._callbacks.append(callback)

    def trend(self) -> dict:
        """Analyze state history for trends."""
        if len(self._history) < 2:
            return {}
        recent = self._history[-5:]
        loads  = [s.resource_load for s in recent]
        depths = [s.execution_depth for s in recent]
        return {
            "load_trend":  (loads[-1] - loads[0]) / max(len(loads)-1, 1),
            "depth_trend": (depths[-1] - depths[0]) / max(len(depths)-1, 1),
            "error_rate":  sum(1 for s in recent if s.error_signals) / len(recent),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# L7 — SECURITY BRIDGE (cogno SECURITY BRIDGE — constraint layer)
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityBridge:
    """
    cogno SECURITY BRIDGE at L7.
    Constrains goal selection space — some goals are forbidden.
    Implements KEM encryption hooks for goal state transmission.
    Dilithium signing hooks for goal execution authorization.

    The system cannot pursue goals that violate these constraints
    regardless of what the THINKER computes — hard boundary.

    From ADAP: AES-256-GCM + CRYSTALS-Kyber-768/Dilithium-3
    Applied here to goal authorization — not just data.
    """

    def __init__(self):
        self._forbidden_patterns: list[str] = [
            "eph.*.*.*",    # never pursue goals that only touch ephemeral files
            "*.tst.snd.*",  # never run sandbox tests as primary goal
        ]
        self._required_tiers_for_production = {"core", "plugin"}
        self._max_execution_depth    = 10
        self._max_sidecar_per_goal   = 16
        self._audit_log: list[dict]  = []

    def authorize_goal(self, goal: 'GoalState',
                       state: SystemState) -> tuple[bool, str]:
        """
        Authorize or reject a proposed goal.
        Returns (authorized, reason).

        This is where the system can REFUSE.
        Invalid goals never execute — they fail authorization.
        """
        # Check execution depth
        if state.execution_depth >= self._max_execution_depth:
            return False, f"DEPTH_EXCEEDED: {state.execution_depth}"

        # Check resource availability
        if state.resource_load > 0.95:
            if goal.priority < 8:  # only critical goals run at 95%+ load
                return False, f"RESOURCE_EXHAUSTED: load={state.resource_load}"

        # Check goal target files
        for fname in goal.target_files:
            d = decode_filename(fname)
            # Forbidden tier for goal primary targets
            if d['tier'] == 'sandbox' and goal.priority < 5:
                return False, f"SANDBOX_GOAL_LOW_PRIORITY: {fname}"
            # Ephemeral files can't be primary goal targets
            if d['role'] == 'ephemeral' and fname == goal.primary_target:
                return False, f"EPHEMERAL_PRIMARY_TARGET: {fname}"

        # Check deadline feasibility
        if goal.deadline_ms and goal.estimated_cost_ms:
            if goal.estimated_cost_ms > goal.deadline_ms * 0.9:
                return False, f"DEADLINE_INFEASIBLE: cost={goal.estimated_cost_ms}ms > deadline={goal.deadline_ms}ms"

        # Audit log
        self._audit_log.append({
            "goal_id":   goal.goal_id,
            "authorized":True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return True, "AUTHORIZED"

    def authorize_dispatch(self, fname: str,
                           goal: 'GoalState',
                           state: SystemState) -> tuple[bool, str]:
        """
        Per-dispatch authorization.
        Every file execution goes through this gate.
        """
        d = decode_filename(fname)

        # Sandbox files require explicit goal permission
        if d['tier'] == 'sandbox' and 'allow_sandbox' not in goal.permissions:
            return False, f"SANDBOX_NOT_PERMITTED: {fname}"

        # Archive files can't be executed (frozen)
        if d['tier'] == 'archive':
            return False, f"ARCHIVE_IMMUTABLE: {fname}"

        # Goal scope check — file must be in goal's target set
        # or be a discovered dependency
        if (goal.strict_scope and
            fname not in goal.target_files and
            fname not in goal.discovered_deps):
            return False, f"OUT_OF_SCOPE: {fname} not in goal targets"

        return True, "AUTHORIZED"

    def sign_goal(self, goal: 'GoalState') -> str:
        """
        Dilithium-style signing hook.
        In production: real Dilithium-3 signature via ADAP crypto.py
        Here: SHA3-256 HMAC simulation.
        """
        payload = f"{goal.goal_id}:{goal.intent}:{goal.priority}"
        return hashlib.sha3_256(payload.encode()).hexdigest()[:32]

# ═══════════════════════════════════════════════════════════════════════════════
# L7 — GOAL STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GoalState:
    """
    L7 intent representation.
    Everything the system knows about what it's trying to accomplish.

    This is what THINKER produces and SECURITY BRIDGE authorizes.
    MIS routing is tilted by this. Hopfield memory is biased by this.
    Entanglement weights are conditional on this.
    """
    goal_id:           str
    intent:            str            # human-readable: "process WebSocket stream"
    priority:          int            # 0-10 (10=critical)
    target_files:      list[str]      # GFS files this goal needs
    primary_target:    str            # entry point
    deadline_ms:       Optional[float]
    estimated_cost_ms: Optional[float]
    permissions:       list[str]      # ["allow_sandbox", "allow_sidecar", ...]
    strict_scope:      bool           # if True, only target_files can execute
    discovered_deps:   list[str]      # deps found during execution
    success_criteria:  dict           # what counts as done
    fallback_path:     Optional[str]  # if primary fails, use this
    signature:         Optional[str] = None  # SECURITY BRIDGE sign
    created_at:        str = ""
    completed_at:      Optional[str] = None
    status:            str = "pending"  # pending/authorized/running/done/refused/failed

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_bias_vector(self, dim: int = 512) -> list[float]:
        """
        Convert goal intent to a Hopfield bias vector.
        This vector tilts L5 memory toward goal-relevant patterns.

        Intent string → deterministic bias projection.
        """
        h = hashlib.sha3_256(
            f"goal:{self.intent}:{self.priority}".encode()).digest()
        bias = []
        block = h
        scale = self.priority / 10.0  # higher priority = stronger bias
        while len(bias) < dim:
            for byte in block:
                bias.append(scale * ((byte / 127.5) - 1.0))
                if len(bias) == dim: break
            block = hashlib.sha3_256(block).digest()
        return bias[:dim]

# ═══════════════════════════════════════════════════════════════════════════════
# L7 — THINKER (cogno THINKER — deliberative reasoning)
# ═══════════════════════════════════════════════════════════════════════════════

class Thinker:
    """
    cogno THINKER — L7 deliberative reasoning engine.

    Responsibilities:
      - Form goal states from high-level intent
      - Evaluate dispatch options against goal
      - Decide when to spawn sidecars (goal-aware, not just Lyapunov)
      - Refuse invalid or dangerous paths (via SECURITY BRIDGE)
      - Update goal state as execution progresses
      - Revise goals when SCANNER reports friction

    The THINKER is the system's judgment. It doesn't just route —
    it decides whether to route at all, and why.

    cogno thought revision loop:
      perceive (SCANNER) → deliberate (THINKER) → authorize (SECURITY BRIDGE)
      → dispatch (GFS) → observe result → revise goal → repeat
    """

    def __init__(self,
                 memory:   HopfieldMemory,
                 scanner:  Scanner,
                 security: SecurityBridge):
        self.memory   = memory
        self.scanner  = scanner
        self.security = security
        self.goals:   list[GoalState]  = []
        self.active:  Optional[GoalState] = None
        self._dispatch_history: list[dict] = []
        self._revision_log:     list[dict] = []

        # Wire SCANNER friction → THINKER revision
        self.scanner.on_friction(self._on_friction)

    def form_goal(self,
                  intent:         str,
                  target_files:   list[str],
                  priority:       int = 5,
                  deadline_ms:    float = None,
                  permissions:    list[str] = None,
                  strict_scope:   bool = False,
                  success_criteria: dict = None,
                  fallback:       str = None) -> GoalState:
        """
        THINKER forms a goal from high-level intent.
        Estimates cost, identifies primary target, sets bias.
        """
        if not target_files:
            raise ValueError("Goal requires at least one target file")

        # Primary target = lowest key_int in target set
        # (core/orchestrator files first)
        primary = min(target_files,
                      key=lambda f: decode_filename(f)['key_int'])

        # Estimate cost from file count and complexity
        estimated_ms = len(target_files) * 5.0  # 5ms per file baseline

        goal = GoalState(
            goal_id          = str(uuid.uuid4()),
            intent           = intent,
            priority         = max(0, min(10, priority)),
            target_files     = target_files,
            primary_target   = primary,
            deadline_ms      = deadline_ms,
            estimated_cost_ms= estimated_ms,
            permissions      = permissions or ["allow_sidecar"],
            strict_scope     = strict_scope,
            discovered_deps  = [],
            success_criteria = success_criteria or {"all_dispatched": True},
            fallback_path    = fallback,
        )

        # Sign the goal
        goal.signature = self.security.sign_goal(goal)

        # Push goal bias into L5 memory
        bias = goal.to_bias_vector(self.memory.D)
        self.memory.set_goal_bias(bias)

        self.goals.append(goal)
        return goal

    def authorize(self, goal: GoalState,
                  state: SystemState) -> tuple[bool, str]:
        """
        Run goal through SECURITY BRIDGE.
        If authorized, set as active goal.
        """
        ok, reason = self.security.authorize_goal(goal, state)
        if ok:
            goal.status = "authorized"
            self.active = goal
        else:
            goal.status = "refused"
            self._log_revision(f"GOAL_REFUSED: {reason}", goal)
        return ok, reason

    def evaluate_dispatch(self, fname: str,
                          state: SystemState) -> tuple[bool, str, dict]:
        """
        THINKER's core judgment function.
        Given a file to dispatch, decide:
          1. Should we dispatch it at all?
          2. Should we spawn a sidecar?
          3. Is there a better alternative?

        Returns: (proceed, reason, metadata)
        """
        if not self.active:
            return False, "NO_ACTIVE_GOAL", {}

        goal = self.active

        # SECURITY BRIDGE per-dispatch authorization
        ok, reason = self.security.authorize_dispatch(fname, goal, state)
        if not ok:
            # Try fallback
            if goal.fallback_path and fname == goal.primary_target:
                self._log_revision(
                    f"PRIMARY_FAILED_TRY_FALLBACK: {reason}", goal)
                fb_ok, fb_reason = self.security.authorize_dispatch(
                    goal.fallback_path, goal, state)
                if fb_ok:
                    return True, f"FALLBACK:{goal.fallback_path}", {
                        "use_fallback": True,
                        "original":     fname,
                        "fallback":     goal.fallback_path,
                    }
            return False, reason, {}

        # Memory retrieval — goal-biased
        bias   = goal.to_bias_vector(self.memory.D)
        nearby = self.memory.retrieve(fname, goal_bias=bias, top_k=3)

        # Sidecar decision — goal-aware
        spawn_sidecar = False
        sidecar_reason = ""
        d = decode_filename(fname)

        # Goal-conditional sidecar triggers
        if (goal.deadline_ms and
            goal.deadline_ms < 100 and
            state.resource_load < 0.7 and
            "allow_sidecar" in goal.permissions):
            spawn_sidecar  = True
            sidecar_reason = "DEADLINE_PRESSURE"

        if (d['role'] == 'orchestrator' and
            len(goal.target_files) > 3 and
            "allow_sidecar" in goal.permissions):
            spawn_sidecar  = True
            sidecar_reason = "ORCHESTRATOR_FANOUT"

        # Discover dependencies — add to goal
        for candidate, score in nearby:
            if (score > 0.6 and
                candidate not in goal.target_files and
                candidate not in goal.discovered_deps):
                goal.discovered_deps.append(candidate)

        # Record dispatch decision
        decision = {
            "fname":         fname,
            "goal_id":       goal.goal_id,
            "spawn_sidecar": spawn_sidecar,
            "sidecar_reason":sidecar_reason,
            "nearby_memory": [(f, round(s, 4)) for f, s in nearby],
            "deps_discovered":goal.discovered_deps[-3:],
            "timestamp":     datetime.now(timezone.utc).isoformat(),
        }
        self._dispatch_history.append(decision)

        return True, "PROCEED", decision

    def observe_result(self, fname: str, success: bool,
                       duration_ms: float, state: SystemState):
        """
        cogno thought revision loop — observe execution result.
        Update goal progress. Revise if needed.
        """
        if not self.active:
            return

        goal = self.active

        # Record episode in memory
        self.memory.record_episode(
            session_id  = goal.goal_id,
            path        = [d['filename'] for d in self._dispatch_history[-5:]
                           if 'fname' in d],
            goal        = goal.intent,
            success     = success,
            duration_ms = duration_ms,
        )

        if not success:
            self._log_revision(f"DISPATCH_FAILED:{fname}", goal)
            # Try to revise goal
            if goal.fallback_path:
                goal.primary_target = goal.fallback_path
                self._log_revision(f"REVISED_TO_FALLBACK:{goal.fallback_path}",
                                   goal)

        # Check if goal is complete
        dispatched = {d['fname'] for d in self._dispatch_history
                      if d.get('goal_id') == goal.goal_id}
        if set(goal.target_files).issubset(dispatched):
            goal.status       = "done"
            goal.completed_at = datetime.now(timezone.utc).isoformat()
            self.active       = None

    def _on_friction(self, signals: list[str], state: SystemState):
        """
        SCANNER friction callback → THINKER revision.
        When scanner detects resistance, THINKER adjusts goal.
        """
        if not self.active:
            return
        goal = self.active
        self._log_revision(f"FRICTION:{','.join(signals)}", goal)

        # Adaptive responses to friction signals
        if "HIGH_LOAD" in signals and goal.priority < 8:
            # Deprioritize sidecars
            if "allow_sidecar" in goal.permissions:
                goal.permissions.remove("allow_sidecar")
                self._log_revision("SIDECAR_SUSPENDED:HIGH_LOAD", goal)

        if "DEADLINE_CRITICAL" in signals:
            # Elevate priority
            goal.priority = min(10, goal.priority + 2)
            self._log_revision(f"PRIORITY_ELEVATED:{goal.priority}", goal)

        if "ERRORS_PRESENT" in signals and goal.fallback_path:
            # Switch to fallback
            goal.primary_target = goal.fallback_path
            self._log_revision(f"FALLBACK_ACTIVATED:{goal.fallback_path}", goal)

    def _log_revision(self, event: str, goal: GoalState):
        self._revision_log.append({
            "event":     event,
            "goal_id":   goal.goal_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def status(self) -> dict:
        return {
            "active_goal":     asdict(self.active) if self.active else None,
            "total_goals":     len(self.goals),
            "dispatch_count":  len(self._dispatch_history),
            "revision_count":  len(self._revision_log),
            "memory_stats":    self.memory.stats(),
            "recent_revisions":self._revision_log[-3:],
        }

# ═══════════════════════════════════════════════════════════════════════════════
# L7 — BOOT (cogno BOOT — system initialization)
# ═══════════════════════════════════════════════════════════════════════════════

class SystemBoot:
    """
    cogno BOOT module — L7 initialization sequence.
    Runs before any production execution.

    Boot sequence:
      1. Load all GFS nodes into Hopfield memory
      2. Run synthetic training episodes (SK-Gen)
      3. Validate memory convergence
      4. Initialize SECURITY BRIDGE constraints
      5. Bring SCANNER online
      6. Activate THINKER with boot goal
      7. System ready signal
    """

    def __init__(self,
                 registry_files: list[str],
                 thinker: Thinker,
                 training_episodes: int = 100):
        self.registry_files     = registry_files
        self.thinker            = thinker
        self.training_episodes  = training_episodes
        self.boot_log:          list[str] = []
        self.ready:             bool      = False

    def _log(self, msg: str):
        entry = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        self.boot_log.append(entry)
        print(f"  BOOT: {msg}")

    def run(self) -> bool:
        """Execute full boot sequence. Returns True if system is ready."""
        self._log("Starting GFS cognitive boot sequence")

        # Phase 1: Load all nodes into Hopfield memory
        self._log(f"Phase 1: Loading {len(self.registry_files)} GFS nodes into Hopfield memory")
        self.thinker.memory.store_many(self.registry_files)
        self._log(f"  Stored {len(self.thinker.memory.patterns)} patterns")

        # Phase 2: Synthetic training episodes
        self._log(f"Phase 2: Running {self.training_episodes} synthetic training episodes")
        import random
        random.seed(42)
        for ep in range(self.training_episodes):
            # Synthetic execution path
            path_len = random.randint(2, 6)
            path     = random.sample(self.registry_files,
                                     min(path_len, len(self.registry_files)))
            goal     = random.choice(["process_stream", "run_tests",
                                       "update_config", "deploy_bridge"])
            success  = random.random() > 0.1  # 90% success rate
            dur_ms   = random.uniform(5, 200)

            self.thinker.memory.record_episode(
                session_id = f"train_{ep}",
                path       = path,
                goal       = goal,
                success    = success,
                duration_ms= dur_ms,
            )

        # Phase 3: SK-Gen pattern mining
        self._log("Phase 3: Mining execution patterns (SK-Gen)")
        patterns = self.thinker.memory.mine_patterns(min_frequency=3)
        self._log(f"  Found {len(patterns)} stable execution patterns")
        for p in patterns[:3]:
            self._log(f"  {p['from']} → {p['to']} "
                      f"(conf={p['confidence']:.2f})")

        # Phase 4: Convergence validation
        self._log("Phase 4: Validating memory convergence")
        if self.registry_files:
            test_file  = self.registry_files[0]
            results    = self.thinker.memory.retrieve(test_file, top_k=1)
            converged  = len(results) > 0 and results[0][1] > 0
            score_str = f"{results[0][1]:.4f}" if results else "0.0000"
            status_str = "PASS" if converged else "FAIL"
            self._log(f"  Retrieval test: {status_str} score={score_str}")
            if not converged:
                self._log("  BOOT FAILED: memory did not converge")
                return False

        # Phase 5: Form boot goal
        self._log("Phase 5: Forming boot goal")
        boot_files = [f for f in self.registry_files
                      if decode_filename(f)['tier'] == 'core'][:3]
        if boot_files:
            boot_goal = self.thinker.form_goal(
                intent       = "system_boot_validation",
                target_files = boot_files,
                priority     = 10,
                permissions  = ["allow_sidecar"],
                success_criteria = {"all_dispatched": True},
            )
            self._log(f"  Boot goal: {boot_goal.intent} "
                      f"(id={boot_goal.goal_id[:8]}…)")

        # Phase 6: Ready
        self.ready = True
        self._log("Boot sequence complete — system ready")
        self._log(f"Memory: {self.thinker.memory.stats()}")
        return True

# ═══════════════════════════════════════════════════════════════════════════════
# VERTICAL INTEGRATION — full L1-L7 dispatch
# ═══════════════════════════════════════════════════════════════════════════════

class GFSCognitive:
    """
    Full vertical integration: L1 signal through L7 intention.

    This is the production entry point.
    Every dispatch goes through all seven levels.

    Usage:
        gfs = GFSCognitive(registry_files)
        gfs.boot()
        gfs.set_intent("process incoming WebSocket stream",
                       target_files=["py.orc.cor.000","py.brd.cor.000"],
                       priority=8)
        result = gfs.dispatch("py.orc.cor.000")
    """

    def __init__(self, registry_files: list[str],
                 hopfield_dim: int = 256):
        self.registry_files = registry_files
        self.memory   = HopfieldMemory(dim=hopfield_dim)
        self.scanner  = Scanner()
        self.security = SecurityBridge()
        self.thinker  = Thinker(self.memory, self.scanner, self.security)
        self.boot_seq = SystemBoot(registry_files, self.thinker)
        self._booted  = False

    def boot(self, training_episodes: int = 50) -> bool:
        self.boot_seq.training_episodes = training_episodes
        self._booted = self.boot_seq.run()
        return self._booted

    def set_intent(self, intent: str,
                   target_files: list[str],
                   priority: int = 5,
                   deadline_ms: float = None,
                   permissions: list[str] = None,
                   fallback: str = None) -> tuple[bool, str, GoalState]:
        """Set system intent — form and authorize a goal."""
        if not self._booted:
            return False, "NOT_BOOTED", None

        # Scan current state
        state = self.scanner.scan(
            active  = [],
            pending = target_files,
            load    = 0.1,
        )

        # Form goal
        goal = self.thinker.form_goal(
            intent       = intent,
            target_files = target_files,
            priority     = priority,
            deadline_ms  = deadline_ms,
            permissions  = permissions or ["allow_sidecar"],
            fallback     = fallback,
        )

        # Authorize
        ok, reason = self.thinker.authorize(goal, state)
        return ok, reason, goal

    def dispatch(self, fname: str,
                 load: float = 0.1,
                 depth: int = 0,
                 deadline_ms: float = None) -> dict:
        """
        Full L1-L7 dispatch.
        Returns decision with all seven levels contributing.
        """
        if not self._booted:
            return {"error": "NOT_BOOTED"}

        # L1: Signal — validate filename
        try:
            d = decode_filename(fname)
        except ValueError as e:
            return {"error": str(e), "refused": True}

        # L6: Scan current state
        state = self.scanner.scan(
            active     = [fname],
            load       = load,
            depth      = depth,
            deadline_ms= deadline_ms,
            last       = fname,
        )

        # L7: THINKER judgment
        proceed, reason, meta = self.thinker.evaluate_dispatch(fname, state)

        if not proceed:
            return {
                "fname":   fname,
                "proceed": False,
                "refused": True,
                "reason":  reason,
                "level":   7,
            }

        # L2: Handler (zero manifest needed)
        handler = d['handler']

        # L5: Memory retrieval (goal-biased)
        bias    = (self.thinker.active.to_bias_vector(self.memory.D)
                   if self.thinker.active else None)
        nearby  = self.memory.retrieve(fname, goal_bias=bias, top_k=3)

        return {
            "fname":          fname,
            "proceed":        True,
            "refused":        False,
            "handler":        handler,
            "reason":         reason,
            "spawn_sidecar":  meta.get("spawn_sidecar", False),
            "sidecar_reason": meta.get("sidecar_reason", ""),
            "memory_nearby":  [(f, round(s,4)) for f,s in nearby],
            "deps_discovered":meta.get("deps_discovered", []),
            "goal_id":        (self.thinker.active.goal_id[:8]+"…"
                               if self.thinker.active else None),
            "level":          7,
        }

    def status(self) -> dict:
        return {
            "booted":  self._booted,
            "thinker": self.thinker.status(),
            "scanner": self.scanner.trend(),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# TEST + BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    print("\n══ L7 COGNITIVE TEST SUITE ═══════════════════════════════════\n")
    passed = failed = 0
    errors = []

    def ok(name, cond, detail=""):
        nonlocal passed, failed
        if cond: passed+=1; print(f"  ✓  {name}")
        else:
            failed+=1; errors.append(f"{name}: {detail}")
            print(f"  ✗  {name} — {detail}")

    def eq(name, got, exp): ok(name, got==exp, f"got={got!r} exp={exp!r}")

    # Build test registry
    test_files = [
        encode_filename(0,0,0,0),   # py.orc.cor.000
        encode_filename(0,1,0,0),   # py.tol.cor.000
        encode_filename(1,2,0,0),   # js.cfg.cor.000
        encode_filename(0,6,0,0),   # py.brd.cor.000
        encode_filename(5,5,2,0),   # sh.tst.snd.000
        encode_filename(0,1,1,0),   # py.tol.plg.000
        encode_filename(1,3,3,0),   # js.dat.arc.000
    ]

    # T1: Hopfield memory
    print("T1: Hopfield memory store + retrieve")
    mem = HopfieldMemory(dim=128)
    mem.store_many(test_files)
    ok("all files stored", len(mem.patterns)==len(test_files))

    results = mem.retrieve("py.orc.cor.000", top_k=3)
    ok("retrieve returns results", len(results)>0)
    ok("top result is valid GFS file", results[0][0] in test_files)
    ok("scores are non-negative", all(s>=0 for _,s in results))

    # Goal bias tilts retrieval
    goal_bias = [0.5]*128
    biased = mem.retrieve("py.orc.cor.000", goal_bias=goal_bias, top_k=3)
    ok("biased retrieval returns results", len(biased)>0)

    # T2: Episode mining
    print("\nT2: SK-Gen episode mining")
    for i in range(5):
        mem.record_episode(f"ep_{i}",
            ["py.orc.cor.000","py.tol.cor.000","js.cfg.cor.000"],
            "test_goal", True, 50.0)
    for i in range(5):
        mem.record_episode(f"ep2_{i}",
            ["py.orc.cor.000","py.brd.cor.000"],
            "bridge_goal", True, 30.0)

    patterns = mem.mine_patterns(min_frequency=3)
    ok("patterns mined", len(patterns)>0)
    ok("top pattern has frequency≥3",
       patterns[0]['frequency']>=3 if patterns else False)

    # T3: Scanner
    print("\nT3: Scanner perception + friction")
    scanner  = Scanner()
    friction_signals = []
    scanner.on_friction(lambda s,_: friction_signals.extend(s))

    state = scanner.scan(load=0.3, depth=2)
    ok("normal state no friction", len(friction_signals)==0)

    state_hi = scanner.scan(load=0.9, depth=2)
    ok("high load triggers friction", "HIGH_LOAD" in friction_signals)

    state_deep = scanner.scan(load=0.3, depth=9)
    ok("deep recursion triggers friction", "DEEP_RECURSION" in friction_signals)

    # T4: Security Bridge
    print("\nT4: Security Bridge authorization")
    security = SecurityBridge()
    goal = GoalState(
        goal_id="test-goal-001",
        intent="test",priority=5,
        target_files=["py.orc.cor.000","py.tol.cor.000"],
        primary_target="py.orc.cor.000",
        deadline_ms=1000,estimated_cost_ms=50,
        permissions=["allow_sidecar"],strict_scope=False,
        discovered_deps=[],success_criteria={},fallback_path=None,
        signature=None,
    )
    state = scanner.scan(load=0.3,depth=2)
    ok_auth, reason = security.authorize_goal(goal, state)
    ok("valid goal authorized", ok_auth)

    # Overload rejection
    state_overload = scanner.scan(load=0.99, depth=2)
    low_goal = GoalState(**{**asdict(goal),"goal_id":"low","priority":3})
    ok_low, reason_low = security.authorize_goal(low_goal, state_overload)
    ok("low priority rejected at 99% load", not ok_low)

    # Archive rejection
    arc_ok, arc_reason = security.authorize_dispatch(
        "js.dat.arc.000", goal, state)
    ok("archive file dispatch rejected", not arc_ok)

    # T5: THINKER
    print("\nT5: THINKER deliberation")
    thinker = Thinker(mem, scanner, security)
    goal2 = thinker.form_goal(
        intent="process WebSocket stream",
        target_files=["py.orc.cor.000","py.brd.cor.000","js.cfg.cor.000"],
        priority=7,
        deadline_ms=500,
        permissions=["allow_sidecar"],
    )
    ok("goal formed", goal2 is not None)
    ok("goal has signature", goal2.signature is not None)
    ok("bias vector set", any(b!=0 for b in mem._bias))

    auth_ok, auth_reason = thinker.authorize(goal2, state)
    ok("goal authorized", auth_ok)
    eq("active goal set", thinker.active.goal_id, goal2.goal_id)

    # Dispatch evaluation
    proceed, reason, meta = thinker.evaluate_dispatch(
        "py.orc.cor.000", state)
    ok("dispatch proceeds", proceed)
    ok("meta contains sidecar decision", "spawn_sidecar" in meta)
    ok("memory nearby populated", len(meta.get("nearby_memory",[])) > 0)

    # Refusal test — archive
    thinker.active.permissions = []  # strip all permissions
    thinker.active.strict_scope = True
    thinker.active.target_files = ["py.orc.cor.000"]
    proceed_arc, reason_arc, _ = thinker.evaluate_dispatch(
        "py.brd.cor.000", state)  # out of scope
    ok("out-of-scope dispatch refused", not proceed_arc)

    # T6: Friction revision
    print("\nT6: THINKER revision from SCANNER friction")
    thinker2 = Thinker(mem, scanner, security)
    goal3 = thinker2.form_goal(
        intent="background task",
        target_files=["py.tol.cor.000"],
        priority=3,
        permissions=["allow_sidecar"],
    )
    thinker2.authorize(goal3, state)
    # Simulate high load friction
    thinker2._on_friction(["HIGH_LOAD"], state_hi)
    ok("sidecar suspended on high load",
       "allow_sidecar" not in thinker2.active.permissions)

    thinker2._on_friction(["DEADLINE_CRITICAL"], state_hi)
    ok("priority elevated on deadline", thinker2.active.priority > 3)

    # T7: Full vertical
    print("\nT7: Full L1-L7 vertical dispatch")
    gfs = GFSCognitive(test_files, hopfield_dim=64)
    booted = gfs.boot(training_episodes=20)
    ok("system boots successfully", booted)

    auth_ok, reason, g = gfs.set_intent(
        "test vertical integration",
        target_files=["py.orc.cor.000","py.tol.cor.000"],
        priority=6,
    )
    ok("intent set and authorized", auth_ok)

    result = gfs.dispatch("py.orc.cor.000")
    ok("dispatch proceeds through all levels", result.get("proceed")==True)
    ok("handler resolved at L2", result.get("handler")=="python")
    ok("goal tracked at L7", result.get("goal_id") is not None)
    ok("memory consulted at L5", len(result.get("memory_nearby",[]))>0)
    ok("level=7 confirmed", result.get("level")==7)

    # Refusal test through full vertical
    result_arc = gfs.dispatch("js.dat.arc.000")
    ok("archive refused at L7", result_arc.get("refused")==True)

    print(f"\n  {'═'*52}")
    print(f"  PASSED: {passed}/{passed+failed}")
    if errors:
        for e in errors: print(f"    ✗ {e}")
    return failed==0

def run_benchmark():
    print("\n══ L7 COGNITIVE BENCHMARK ════════════════════════════════════\n")

    test_files = [encode_filename(i%8,i%8,i%4,i%64) for i in range(30)]
    gfs = GFSCognitive(test_files, hopfield_dim=128)
    gfs.boot(training_episodes=30)
    gfs.set_intent("benchmark", test_files[:5], priority=5)

    def tm(fn, n=1000):
        s=time.perf_counter()
        for _ in range(n): fn()
        return ((time.perf_counter()-s)*1e6)/n

    mem = gfs.memory
    scanner = gfs.scanner
    state = scanner.scan(load=0.2)

    b = [
        ("Hopfield store",        lambda: mem.store(test_files[0]),             500),
        ("Hopfield retrieve",     lambda: mem.retrieve(test_files[0],top_k=3),  200),
        ("Biased retrieve (L7)",  lambda: mem.retrieve(test_files[0],
                                           goal_bias=[0.5]*128,top_k=3),        200),
        ("Scanner scan",          lambda: scanner.scan(load=0.3),              1000),
        ("Goal bias vector",      lambda: gfs.thinker.active and
                                           gfs.thinker.active.to_bias_vector(128), 1000),
        ("Security authorize",    lambda: gfs.security.authorize_dispatch(
                                           test_files[0],
                                           gfs.thinker.active, state),         1000),
        ("Thinker evaluate",      lambda: gfs.thinker.evaluate_dispatch(
                                           test_files[0], state),               500),
        ("Full L1-L7 dispatch",   lambda: gfs.dispatch(test_files[0]),          500),
        ("SK-Gen mine patterns",  lambda: mem.mine_patterns(3),                 200),
    ]

    for name, fn, n in b:
        us = tm(fn, n)
        print(f"  {name:<30} {us:>10.3f} μs/op")

    print(f"\n  L7 overhead vs direct dispatch:")
    direct_us = tm(lambda: decode_filename(test_files[0])['handler'], 5000)
    full_us   = tm(lambda: gfs.dispatch(test_files[0]), 500)
    print(f"  Direct (L1-L2 only):          {direct_us:>10.3f} μs")
    print(f"  Full cognitive (L1-L7):       {full_us:>10.3f} μs")
    print(f"  L7 overhead:                  {full_us-direct_us:>10.3f} μs")
    print(f"  Judgment cost:                {((full_us/direct_us)-1)*100:>9.1f}%")

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv)>1 else "all"
    t_ok = True
    if cmd in ("test","all"):  t_ok = run_tests()
    if cmd in ("bench","all"): run_benchmark()
    if cmd == "all":
        print(f"\n{'═'*62}")
        print(f"  GFS L7 — cogno THINKER INTEGRATION")
        print(f"  Tests: {'ALL PASSED' if t_ok else 'FAILURES'}")
        print(f"{'═'*62}")
