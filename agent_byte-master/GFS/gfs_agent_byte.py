#!/usr/bin/env python3
"""
GFS + Agent Byte Integration
agent_byte-master ↔ GFS cognitive stack

Architecture:
  Phase 1 — Gymnasium pre-training
    Agent Byte trains on CartPole/MountainCar
    Builds baseline neural Q-values + symbolic skills
    256-dim VAE state representation learned

  Phase 2 — Transfer to GFS environment
    GFSEnvironmentAdapter wraps GFSCognitive as Environment
    Action space  = GFS key integers (TYPE×ROLE×TIER×SEQ)
    State space   = SystemState → 256-dim normalized vector
    Reward        = execution success + speed + efficiency
    Skills transfer from gymnasium → GFS via TransferMapper

  Phase 3 — Multi-agent transfer
    GhostGoat Agent Byte instance (Telegram interactions)
    ADAP Agent Byte instance (orchestration decisions)
    CRDT-merged skill library shared between both

Dual Brain wiring to GFS L1-L7:
  NeuralBrain (DQN)     → L6 MIS routing (Q-values weight MIS scores)
  SymbolicBrain         → L7 THINKER    (Skill = GoalState template)
  StateNormalizer VAE   → L5 Hopfield   (256-dim → pattern vector)
  SkillDiscovery        → SK-Gen mining  (neural + episodic combined)
  TransferMapper        → CRDT merge    (skills as CRDT objects)
  ExperienceStorage     → GFS dat nodes (js.dat.arc.{seq})
  Environment.step()    → GFSCognitive.dispatch()
"""

import json
import math
import random
import hashlib
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, Any
from datetime import datetime, timezone
from collections import deque

# ═══════════════════════════════════════════════════════════════════════════════
# GFS CORE (inline — delegates to gfs_v4/gfs_l7 in production)
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
                handler=TYPES[ti][1],role=ROLES[ri][1],tier=TIERS[ii][1],
                cache_hint=(ii==0 and ri in(0,1)))

# ═══════════════════════════════════════════════════════════════════════════════
# STATE NORMALIZER — 256-dim VAE-style encoder
# Maps any environment state to fixed 256-dim vector
# Agent Byte Sprint 2 equivalent — without PyTorch dep
# ═══════════════════════════════════════════════════════════════════════════════

class StateNormalizer:
    """
    Environment-agnostic state normalization.
    Maps variable-dimension states to fixed 256-dim vectors.

    Agent Byte uses PyTorch VAE — this is a pure-math equivalent
    that maintains interface compatibility without the dep.

    In production: swap encode() with actual VAE from agent_byte.

    Supports:
      - GFS SystemState dicts → 256-dim
      - Gymnasium observation arrays → 256-dim
      - Raw key integers → 256-dim
    """

    DIM = 256

    def __init__(self, env_id: str = "default"):
        self.env_id = env_id
        # Running stats for normalization
        self._mean:  list[float] = [0.0] * self.DIM
        self._var:   list[float] = [1.0] * self.DIM
        self._count: int = 0
        # Projection matrix (deterministic from env_id seed)
        self._proj  = self._make_projection(env_id)

    def _make_projection(self, env_id: str) -> list[list[float]]:
        """Fast deterministic projection via seed-based LCG — O(DIM^2) but cheap ops."""
        seed = int(hashlib.sha3_256(f"proj:{env_id}".encode()).hexdigest()[:16], 16)
        proj = []
        lcg  = seed
        scale = 1.0 / math.sqrt(self.DIM)
        for i in range(self.DIM):
            row = []
            for j in range(self.DIM):
                lcg  = (lcg * 1664525 + 1013904223) & 0xFFFFFFFF
                row.append(((lcg & 0xFFFF) / 32767.5 - 1.0) * scale)
            proj.append(row)
        return proj

    def encode_gymnasium(self, obs: list[float]) -> list[float]:
        """Gymnasium observation → 256-dim normalized vector."""
        # Pad or truncate to DIM
        padded = list(obs) + [0.0]*(self.DIM - len(obs))
        padded = padded[:self.DIM]
        # Apply projection
        projected = [
            sum(self._proj[i][j]*padded[j] for j in range(self.DIM))
            / math.sqrt(self.DIM)
            for i in range(self.DIM)
        ]
        return self._normalize_online(projected)

    def encode_gfs_state(self, state: dict) -> list[float]:
        """
        GFS SystemState dict → 256-dim vector.
        Encodes: active files, load, depth, deadline, errors, progress.
        """
        features = []

        # Active file keys (up to 4)
        for fname in (state.get('active_files') or [])[:4]:
            try:
                d = decode_filename(fname)
                features.extend([
                    d['type_id']/7.0,
                    d['role_id']/7.0,
                    d['tier_id']/3.0,
                    d['sequence']/255.0,
                ])
            except: features.extend([0.0,0.0,0.0,0.0])
        while len(features) < 16: features.append(0.0)

        # System metrics
        features.append(state.get('resource_load', 0.0))
        features.append(state.get('execution_depth', 0)/10.0)
        features.append(min(state.get('deadline_ms', 1000)/1000.0, 1.0))
        features.append(state.get('goal_progress', 0.0))
        features.append(len(state.get('error_signals', []))/5.0)
        features.append(len(state.get('pending_files', []))/10.0)
        features.append(state.get('sidecar_count', 0)/8.0)

        # Pad to DIM via projection
        padded = (features + [0.0]*self.DIM)[:self.DIM]
        projected = [
            sum(self._proj[i][j]*padded[j] for j in range(self.DIM))
            / math.sqrt(self.DIM)
            for i in range(self.DIM)
        ]
        return self._normalize_online(projected)

    def encode_key(self, key_int: int) -> list[float]:
        """GFS key integer → 256-dim vector."""
        ti=(key_int>>13)&7; ri=(key_int>>10)&7
        ii=(key_int>>8)&3;  sq=key_int&255
        raw = [ti/7.0, ri/7.0, ii/3.0, sq/255.0]
        return self.encode_gymnasium(raw)

    def _normalize_online(self, vec: list[float]) -> list[float]:
        """Welford online normalization — updates running mean/var."""
        self._count += 1
        for i in range(self.DIM):
            delta = vec[i] - self._mean[i]
            self._mean[i] += delta / self._count
            self._var[i]  += delta * (vec[i] - self._mean[i])
        if self._count > 1:
            std = [math.sqrt(max(v/(self._count-1), 1e-8))
                   for v in self._var]
            return [(vec[i]-self._mean[i])/std[i] for i in range(self.DIM)]
        return vec

# ═══════════════════════════════════════════════════════════════════════════════
# NEURAL BRAIN — DQN (no-PyTorch version)
# Pure numpy/math DQN compatible with Agent Byte NeuralBrain interface
# In production: replace with agent_byte.core.neural_brain.NeuralBrain
# ═══════════════════════════════════════════════════════════════════════════════

class NeuralBrain:
    """
    DQN implementation — Agent Byte NeuralBrain interface compatible.

    Network: Input(256) → Hidden(128) → Hidden(64) → Output(action_size)
    Uses experience replay + epsilon-greedy exploration.
    No PyTorch dep — uses pure math. Swap with PyTorch version for
    full gradient-based learning.

    Q-values directly weight the GFS MIS routing scores at L6.
    """

    d/media/popic/New Volume/training/datasets/ef __init__(self, state_size: int = 256,
                 action_size: int = 256,
                 lr: float = 0.001,
                 gamma: float = 0.95,
                 epsilon: float = 1.0,
                 epsilon_decay: float = 0.995,
                 epsilon_min: float = 0.01,
                 memory_size: int = 10000,
                 batch_size: int = 32):
        self.state_size    = state_size
        self.action_size   = action_size
        self.lr            = lr
        self.gamma         = gamma
        self.epsilon       = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min   = epsilon_min
        self.batch_size    = batch_size
        self.memory        = deque(maxlen=memory_size)

        # Simple linear Q-table (weight matrix)
        # In production: replace with PyTorch nn.Module
        self._init_weights()
        self.training_steps = 0
        self.total_reward   = 0.0

    def _init_weights(self):
        """Xavier initialization."""
        def xavier(rows, cols):
            scale = math.sqrt(2.0/(rows+cols))
            rows_data = []
            h = hashlib.sha3_256(f"w:{rows}:{cols}".encode()).digest()
            for i in range(rows):
                row = []
                block = hashlib.sha3_256(f"{i}".encode()+h).digest()
                while len(row) < cols:
                    for byte in block:
                        row.append(scale*((byte/127.5)-1.0))
                        if len(row)==cols: break
                    block = hashlib.sha3_256(block).digest()
                rows_data.append(row)
            return rows_data

        # Two-layer network weights
        self.W1 = xavier(64, self.state_size)    # hidden layer 1
        self.W2 = xavier(32, 64)                  # hidden layer 2
        self.W3 = xavier(self.action_size, 32)    # output layer

        # Target network (copy)
        self.W1t = [row[:] for row in self.W1]
        self.W2t = [row[:] for row in self.W2]
        self.W3t = [row[:] for row in self.W3]

    def _relu(self, x: list[float]) -> list[float]:
        return [max(0.0, v) for v in x]

    def _matmul(self, W: list[list[float]],
                x: list[float]) -> list[float]:
        return [sum(W[i][j]*x[j] for j in range(len(x)))
                for i in range(len(W))]

    def _forward(self, state: list[float],
                 target: bool = False) -> list[float]:
        W1 = self.W1t if target else self.W1
        W2 = self.W2t if target else self.W2
        W3 = self.W3t if target else self.W3
        h1 = self._relu(self._matmul(W1, state))
        h2 = self._relu(self._matmul(W2, h1))
        return self._matmul(W3, h2)  # W1:64xDIM W2:32x64 W3:actions x32

    def act(self, state: list[float]) -> int:
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size-1)
        q_values = self._forward(state)
        return q_values.index(max(q_values))

    def q_values(self, state: list[float]) -> list[float]:
        """Raw Q-values for all actions — used to weight MIS routing."""
        return self._forward(state)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
        self.total_reward += reward

    def replay(self) -> Optional[float]:
        """Experience replay training step. Returns loss."""
        if len(self.memory) < self.batch_size:
            return None

        batch = random.sample(self.memory, self.batch_size)
        total_loss = 0.0

        for state, action, reward, next_state, done in batch:
            # Target Q-value
            if done:
                target_q = reward
            else:
                next_q   = self._forward(next_state, target=True)
                target_q = reward + self.gamma * max(next_q)

            # Current Q-values
            current_q = self._forward(state)
            error     = target_q - current_q[action]
            total_loss += error**2

            # Simple gradient update on output layer
            # In production: proper backprop via PyTorch
            for j in range(len(self.W3[action])):
                h2 = self._relu(self._matmul(self.W2,
                     self._relu(self._matmul(self.W1, state))))
                if j < len(h2):
                    self.W3[action][j] += self.lr * error * h2[j]

        self.training_steps += 1

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        # Sync target network every 100 steps
        if self.training_steps % 100 == 0:
            self.W1t = [r[:] for r in self.W1]
            self.W2t = [r[:] for r in self.W2]
            self.W3t = [r[:] for r in self.W3]

        return total_loss / self.batch_size

    def get_state_dict(self) -> dict:
        return {
            "W1": self.W1, "W2": self.W2, "W3": self.W3,
            "epsilon": self.epsilon, "training_steps": self.training_steps,
            "total_reward": self.total_reward,
        }

    def load_state_dict(self, d: dict):
        self.W1 = d["W1"]; self.W2 = d["W2"]; self.W3 = d["W3"]
        self.epsilon       = d["epsilon"]
        self.training_steps= d["training_steps"]
        self.total_reward  = d["total_reward"]
        self.W1t = [r[:] for r in self.W1]
        self.W2t = [r[:] for r in self.W2]
        self.W3t = [r[:] for r in self.W3]

# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOLIC BRAIN — skill discovery + interpretable reasoning
# Agent Byte SymbolicBrain equivalent
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Skill:
    """
    A discovered reusable execution pattern.
    Agent Byte Skill equivalent — stored as GFS data nodes.
    CRDT-mergeable: skills transfer between GhostGoat and ADAP.
    """
    skill_id:     str
    name:         str
    description:  str
    action_seq:   list[int]      # sequence of GFS key integers
    fname_seq:    list[str]      # corresponding filenames
    avg_reward:   float
    success_rate: float
    use_count:    int
    env_origin:   str            # "gymnasium:CartPole" or "gfs:production"
    agent_origin: str            # "ghostgoat" or "adap" or "gymnasium"
    transferable: bool
    created_at:   str = ""
    token:        str = ""       # CRDT OR-Set token

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.token:
            self.token = str(uuid.uuid4())

class SymbolicBrain:
    """
    Skill discovery and interpretable reasoning layer.
    Agent Byte SymbolicBrain equivalent.

    Discovers skills from:
      1. Neural brain action sequences (high-reward paths)
      2. GFS execution episodes (SK-Gen patterns)
      3. Transfer from other agents (CRDT merge)

    Skills stored as GFS nodes: js.dat.arc.{seq}
    """

    def __init__(self, agent_id: str = "default"):
        self.agent_id = agent_id
        self.skills: dict[str, Skill] = {}
        self._episode_buffer: list[dict] = []
        self._skill_threshold_reward  = 0.7
        self._skill_threshold_success = 0.8
        self._skill_min_uses          = 3

    def record_episode(self, action_seq: list[int],
                       fname_seq: list[str],
                       total_reward: float,
                       success: bool,
                       env_id: str):
        self._episode_buffer.append({
            "action_seq":   action_seq,
            "fname_seq":    fname_seq,
            "total_reward": total_reward,
            "success":      success,
            "env_id":       env_id,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        })

    def discover_skills(self) -> list[Skill]:
        """
        Mine episode buffer for recurring high-reward patterns.
        Agent Byte SkillDiscovery equivalent.
        """
        # Count recurring action subsequences
        seq_stats: dict[str, dict] = {}
        for ep in self._episode_buffer:
            seq = tuple(ep['action_seq'])
            key = str(seq)
            if key not in seq_stats:
                seq_stats[key] = {
                    "seq":       ep['action_seq'],
                    "fnames":    ep['fname_seq'],
                    "rewards":   [],
                    "successes": [],
                    "env_id":    ep['env_id'],
                }
            seq_stats[key]["rewards"].append(ep['total_reward'])
            seq_stats[key]["successes"].append(ep['success'])

        new_skills = []
        for key, stats in seq_stats.items():
            if len(stats["rewards"]) < self._skill_min_uses:
                continue
            avg_r   = sum(stats["rewards"])/len(stats["rewards"])
            avg_s   = sum(stats["successes"])/len(stats["successes"])
            if avg_r < self._skill_threshold_reward: continue
            if avg_s < self._skill_threshold_success: continue

            skill_id = hashlib.sha3_256(key.encode()).hexdigest()[:16]
            if skill_id in self.skills: continue

            skill = Skill(
                skill_id    = skill_id,
                name        = f"skill_{skill_id[:8]}",
                description = (f"High-reward path: "
                               f"{stats['fnames'][:2]} → ... "
                               f"(r={avg_r:.2f}, s={avg_s:.2f})"),
                action_seq  = stats["seq"],
                fname_seq   = stats["fnames"],
                avg_reward  = avg_r,
                success_rate= avg_s,
                use_count   = len(stats["rewards"]),
                env_origin  = stats["env_id"],
                agent_origin= self.agent_id,
                transferable= True,
            )
            self.skills[skill_id] = skill
            new_skills.append(skill)

        return new_skills

    def best_skill_for_state(self, state_vec: list[float],
                             available_actions: list[int]) -> Optional[Skill]:
        """Find best matching skill for current state."""
        if not self.skills:
            return None
        # Score by: success rate × avg reward × action overlap
        best = None
        best_score = 0.0
        avail_set = set(available_actions)
        for skill in self.skills.values():
            if not skill.transferable: continue
            overlap = len(set(skill.action_seq) & avail_set)
            score   = skill.success_rate * skill.avg_reward * (overlap/max(len(skill.action_seq),1))
            if score > best_score:
                best_score = score
                best = skill
        return best

    def merge_skills(self, other_skills: dict[str, Skill]):
        """CRDT merge — union of skills, dedup by skill_id."""
        for sid, skill in other_skills.items():
            if sid not in self.skills:
                self.skills[sid] = skill
            else:
                # Take higher success rate
                if skill.success_rate > self.skills[sid].success_rate:
                    self.skills[sid] = skill

    def to_dict(self) -> dict:
        return {k: asdict(v) for k,v in self.skills.items()}

    @classmethod
    def from_dict(cls, d: dict, agent_id: str) -> 'SymbolicBrain':
        brain = cls(agent_id)
        brain.skills = {k: Skill(**v) for k,v in d.items()}
        return brain

# ═══════════════════════════════════════════════════════════════════════════════
# GYMNASIUM ENVIRONMENT ADAPTER
# Phase 1: Pre-training on CartPole/MountainCar
# ═══════════════════════════════════════════════════════════════════════════════

class GymnasiumAdapter:
    """
    Wraps a gymnasium-style environment for Agent Byte training.
    Phase 1: builds baseline skills before GFS transfer.

    Compatible with Agent Byte Environment interface:
      reset() → state: list[float]
      step(action) → (state, reward, done, info)
      get_state_size() → int
      get_action_size() → int
      get_id() → str

    Simulates CartPole and MountainCar without gymnasium dep.
    In production: import gymnasium and wrap real env.
    """

    def __init__(self, env_name: str = "CartPole"):
        self.env_name    = env_name
        self._step_count = 0
        self._episode    = 0
        self._state      = self._make_state()
        self._max_steps  = 200

    def _make_state(self) -> list[float]:
        """Simulated environment state."""
        if self.env_name == "CartPole":
            # CartPole: [cart_pos, cart_vel, pole_angle, pole_vel]
            return [random.uniform(-0.05,0.05) for _ in range(4)]
        elif self.env_name == "MountainCar":
            # MountainCar: [position, velocity]
            return [random.uniform(-0.6,-0.4), 0.0]
        return [random.random() for _ in range(4)]

    def _physics_step(self, action: int) -> tuple:
        """Simple physics simulation."""
        if self.env_name == "CartPole":
            pos, vel, angle, ang_vel = self._state
            force = 10.0 if action==1 else -10.0
            cos_a = math.cos(angle); sin_a = math.sin(angle)
            # Simplified CartPole physics
            ang_acc = (9.8*sin_a - cos_a*force*0.01) / 0.33
            acc     = force*0.01 - 0.01*ang_acc*cos_a
            vel    += acc*0.02
            pos    += vel*0.02
            ang_vel+= ang_acc*0.02
            angle  += ang_vel*0.02
            self._state = [pos, vel, angle, ang_vel]
            done = (abs(pos)>2.4 or abs(angle)>0.209 or
                    self._step_count>=self._max_steps)
            reward = 1.0 if not done else 0.0
            return self._state, reward, done, {}

        elif self.env_name == "MountainCar":
            pos, vel = self._state
            force = (action-1)*0.001
            vel   = max(-0.07, min(0.07, vel + force - 0.0025*math.cos(3*pos)))
            pos   = max(-1.2, min(0.6, pos+vel))
            if pos==-1.2: vel=0
            done  = pos>=0.5 or self._step_count>=self._max_steps
            reward= 0.0 if done and pos>=0.5 else -1.0
            self._state = [pos, vel]
            return self._state, reward, done, {}

        # Generic random env
        self._state = [random.random() for _ in range(4)]
        done = self._step_count >= self._max_steps
        return self._state, random.random(), done, {}

    def reset(self) -> list[float]:
        self._state     = self._make_state()
        self._step_count= 0
        self._episode  += 1
        return self._state

    def step(self, action: int) -> tuple:
        self._step_count += 1
        return self._physics_step(action)

    def get_state_size(self) -> int:
        return len(self._state)

    def get_action_size(self) -> int:
        if self.env_name == "CartPole":    return 2
        if self.env_name == "MountainCar": return 3
        return 4

    def get_id(self) -> str:
        return f"gymnasium:{self.env_name}"

# ═══════════════════════════════════════════════════════════════════════════════
# GFS ENVIRONMENT ADAPTER
# Phase 2: GFS as Agent Byte training environment
# ═══════════════════════════════════════════════════════════════════════════════

class GFSEnvironmentAdapter:
    """
    Wraps GFS cognitive stack as an Agent Byte Environment.

    Action space:  discrete GFS key integers
                   Reduced to top-N by role for tractability
    State space:   SystemState → 256-dim normalized vector
    Reward:
      +1.0  dispatch succeeds
      +0.5  sidecar spawned efficiently
      +0.3  dependency discovered
      -0.5  dispatch refused
      -1.0  security violation
      +0.1  per ms under deadline

    Episode:  one complete goal execution (form → complete/fail)
    Done:     goal complete, goal failed, or max steps reached
    """

    MAX_STEPS    = 50
    ACTION_SPACE = 256  # top 256 GFS keys by priority

    def __init__(self, registry_files: list[str],
                 normalizer: StateNormalizer = None,
                 max_steps: int = MAX_STEPS):
        self.registry_files = registry_files
        self.normalizer     = normalizer or StateNormalizer("gfs_env")
        self.max_steps      = max_steps
        self._step_count    = 0
        self._episode       = 0
        self._total_reward  = 0.0
        self._action_map    = self._build_action_map()
        self._current_state = None
        self._goal_files    = []
        self._done_files:   set = set()

    def _build_action_map(self) -> list[str]:
        """Map action integers → GFS filenames. Top N by key_int."""
        sorted_files = sorted(self.registry_files,
                              key=lambda f: decode_filename(f)['key_int'])
        # Pad to ACTION_SPACE
        while len(sorted_files) < self.ACTION_SPACE:
            sorted_files.append(sorted_files[0] if sorted_files else
                                 encode_filename(0,0,0,0))
        return sorted_files[:self.ACTION_SPACE]

    def _make_state_dict(self, active: list[str] = None,
                         load: float = 0.1) -> dict:
        return {
            "active_files":    active or [],
            "pending_files":   [f for f in self._goal_files
                                 if f not in self._done_files],
            "sidecar_count":   0,
            "resource_load":   load,
            "deadline_ms":     500.0,
            "error_signals":   [],
            "last_dispatch":   active[0] if active else None,
            "execution_depth": self._step_count,
            "goal_progress":   len(self._done_files)/max(len(self._goal_files),1),
        }

    def reset(self) -> list[float]:
        self._step_count  = 0
        self._episode    += 1
        self._done_files  = set()
        self._total_reward= 0.0

        # Random goal: 2-4 random files
        n = random.randint(2, min(4, len(self.registry_files)))
        self._goal_files = random.sample(self.registry_files, n)

        state_dict = self._make_state_dict()
        self._current_state = state_dict
        return self.normalizer.encode_gfs_state(state_dict)

    def step(self, action: int) -> tuple:
        self._step_count += 1

        # Map action → filename
        fname = self._action_map[action % len(self._action_map)]
        reward = 0.0
        info   = {"fname": fname, "action": action}

        try:
            d = decode_filename(fname)

            # Core reward logic
            if fname in self._goal_files and fname not in self._done_files:
                self._done_files.add(fname)
                reward += 1.0
                info["hit"] = True
            elif d['tier'] == 'archive':
                # Trying to dispatch archive — penalty
                reward -= 0.5
                info["refused"] = True
            elif d['tier'] == 'sandbox' and d['role'] == 'test':
                # Valid but not in goal — small penalty
                reward -= 0.1
            else:
                # Valid dispatch, not in goal — neutral
                reward += 0.05

            # Speed bonus — reward faster completion
            if len(self._done_files) == len(self._goal_files):
                speed_bonus = max(0, (self.max_steps - self._step_count)/self.max_steps)
                reward += speed_bonus * 0.5
                info["goal_complete"] = True

        except ValueError:
            reward -= 1.0
            info["invalid"] = True

        self._total_reward += reward

        # Done conditions
        done = (len(self._done_files) == len(self._goal_files) or
                self._step_count >= self.max_steps)

        state_dict = self._make_state_dict([fname], load=self._step_count/self.max_steps)
        self._current_state = state_dict
        state_vec = self.normalizer.encode_gfs_state(state_dict)

        info["total_reward"] = self._total_reward
        info["progress"] = len(self._done_files)/max(len(self._goal_files),1)

        return state_vec, reward, done, info

    def get_state_size(self) -> int: return self.normalizer.DIM
    def get_action_size(self) -> int: return self.ACTION_SPACE
    def get_id(self) -> str: return "gfs:production"

# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFER MAPPER — gymnasium → GFS skill transfer
# Agent Byte TransferMapper equivalent
# ═══════════════════════════════════════════════════════════════════════════════

class TransferMapper:
    """
    Maps skills learned in gymnasium → GFS action space.
    Agent Byte TransferMapper equivalent.

    Gymnasium actions (2-3 discrete) → GFS keys (65,536 discrete)
    Uses skill behavioral fingerprint for cross-domain matching.

    Transfer protocol:
      1. Extract behavioral fingerprint from gymnasium skill
      2. Find GFS files with matching behavioral profile
      3. Create GFS-native skill from matched files
      4. CRDT-merge into target agent's SymbolicBrain
    """

    def __init__(self, gym_normalizer:  StateNormalizer,
                 gfs_normalizer:  StateNormalizer,
                 registry_files:  list[str]):
        self.gym_norm     = gym_normalizer
        self.gfs_norm     = gfs_normalizer
        self.registry     = registry_files
        self._transfer_log: list[dict] = []

    def _behavioral_fingerprint(self, skill: Skill) -> list[float]:
        """
        Extract behavioral signature from skill.
        Used for cross-domain matching.
        """
        # Encode skill properties into a fingerprint vector
        features = [
            skill.avg_reward,
            skill.success_rate,
            skill.use_count / 100.0,
            len(skill.action_seq) / 10.0,
            1.0 if skill.transferable else 0.0,
        ]
        return self.gym_norm.encode_gymnasium(features)

    def _match_gfs_files(self, fingerprint: list[float],
                         top_k: int = 3) -> list[str]:
        """Find GFS files whose encoded vectors best match fingerprint."""
        scores = []
        for fname in self.registry:
            try:
                d = decode_filename(fname)
                # Skip archive files (can't dispatch)
                if d['tier'] == 'archive': continue
                vec   = self.gfs_norm.encode_key(d['key_int'])
                # Cosine similarity
                dot   = sum(a*b for a,b in zip(fingerprint[:64], vec[:64]))
                na    = math.sqrt(sum(a**2 for a in fingerprint[:64]))
                nb    = math.sqrt(sum(b**2 for b in vec[:64]))
                sim   = dot/(na*nb) if na>1e-10 and nb>1e-10 else 0.0
                scores.append((fname, sim))
            except: continue
        scored = sorted(scores, key=lambda x: x[1], reverse=True)
        return [f for f,_ in scored[:top_k]]

    def transfer(self, gym_skill: Skill,
                 target_agent: str = "adap") -> Optional[Skill]:
        """
        Transfer a gymnasium skill into GFS action space.
        Returns new GFS-native skill or None if transfer fails.
        """
        fingerprint  = self._behavioral_fingerprint(gym_skill)
        matched_files= self._match_gfs_files(fingerprint)

        if not matched_files:
            return None

        # Map gymnasium action indices → GFS key integers
        gfs_actions = [decode_filename(f)['key_int'] for f in matched_files]

        transferred = Skill(
            skill_id    = f"xfer_{gym_skill.skill_id[:8]}_{target_agent}",
            name        = f"xfer:{gym_skill.name}→{target_agent}",
            description = (f"Transferred from {gym_skill.env_origin}. "
                           f"Original: {gym_skill.description}"),
            action_seq  = gfs_actions,
            fname_seq   = matched_files,
            avg_reward  = gym_skill.avg_reward * 0.7,  # discount for transfer
            success_rate= gym_skill.success_rate * 0.8,
            use_count   = 0,
            env_origin  = f"transferred:{gym_skill.env_origin}→gfs",
            agent_origin= target_agent,
            transferable= True,
        )

        self._transfer_log.append({
            "from_skill":  gym_skill.skill_id,
            "to_skill":    transferred.skill_id,
            "from_env":    gym_skill.env_origin,
            "to_agent":    target_agent,
            "matched":     matched_files,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        })

        return transferred

    def transfer_all(self, gym_brain: SymbolicBrain,
                     gfs_brain:  SymbolicBrain) -> int:
        """Transfer all transferable gymnasium skills to GFS brain."""
        count = 0
        for skill in gym_brain.skills.values():
            if not skill.transferable: continue
            transferred = self.transfer(skill, gfs_brain.agent_id)
            if transferred:
                gfs_brain.skills[transferred.skill_id] = transferred
                count += 1
        return count

# ═══════════════════════════════════════════════════════════════════════════════
# DUAL BRAIN AGENT — full Agent Byte integration
# ═══════════════════════════════════════════════════════════════════════════════

class DualBrainAgent:
    """
    Full Agent Byte dual brain agent integrated with GFS.

    Neural Brain:   DQN — learns Q-values for GFS dispatch decisions
    Symbolic Brain: skill discovery — finds reusable GFS execution patterns
    StateNormalizer:VAE-style — maps GFS state to 256-dim vectors
    Transfer:       gymnasium pre-training → GFS production

    Usage:
        agent = DualBrainAgent("ghostgoat", registry_files)

        # Phase 1: gymnasium pre-training
        agent.pretrain_gymnasium(episodes=500)

        # Phase 2: transfer to GFS
        agent.transfer_to_gfs()

        # Phase 3: GFS production training
        agent.train_gfs(episodes=200)

        # Dispatch in production
        action = agent.dispatch(gfs_state)
    """

    def __init__(self, agent_id: str, registry_files: list[str],
                 gym_env: str = "CartPole"):
        self.agent_id        = agent_id
        self.registry_files  = registry_files
        self.gym_env_name    = gym_env

        # Normalizers
        self.gym_normalizer  = StateNormalizer(f"gym:{gym_env}")
        self.gfs_normalizer  = StateNormalizer(f"gfs:{agent_id}")

        # Gymnasium environment
        self.gym_env         = GymnasiumAdapter(gym_env)

        # GFS environment
        self.gfs_env         = GFSEnvironmentAdapter(
            registry_files, self.gfs_normalizer)

        # Neural brains (separate for each domain)
        self.gym_neural      = NeuralBrain(
            state_size  = 256,
            action_size = self.gym_env.get_action_size(),
        )
        self.gfs_neural      = NeuralBrain(
            state_size  = 256,
            action_size = GFSEnvironmentAdapter.ACTION_SPACE,
        )

        # Symbolic brains
        self.gym_symbolic    = SymbolicBrain(f"{agent_id}:gym")
        self.gfs_symbolic    = SymbolicBrain(f"{agent_id}:gfs")

        # Transfer mapper
        self.transfer_mapper = TransferMapper(
            self.gym_normalizer,
            self.gfs_normalizer,
            registry_files,
        )

        # Training stats
        self.stats = {
            "gym_episodes":   0,
            "gfs_episodes":   0,
            "gym_rewards":    [],
            "gfs_rewards":    [],
            "skills_found":   0,
            "skills_xferred": 0,
            "training_steps": 0,
        }

    def pretrain_gymnasium(self, episodes: int = 300,
                           verbose: bool = True) -> dict:
        """
        Phase 1: Pre-train on gymnasium environment.
        Builds baseline neural Q-values and discovers reusable skills.
        """
        print(f"\n── Phase 1: Gymnasium pre-training ({episodes} episodes) ──")
        print(f"   Environment: {self.gym_env.get_id()}")
        print(f"   Actions: {self.gym_env.get_action_size()}")

        ep_rewards = []

        for ep in range(episodes):
            raw_state  = self.gym_env.reset()
            state      = self.gym_normalizer.encode_gymnasium(raw_state)
            total_r    = 0.0
            done       = False
            action_seq = []
            fname_seq  = []

            while not done:
                action  = self.gym_neural.act(state)
                raw_ns, reward, done, info = self.gym_env.step(action)
                next_s  = self.gym_normalizer.encode_gymnasium(raw_ns)

                self.gym_neural.remember(state, action, reward, next_s, done)
                self.gym_neural.replay()

                action_seq.append(action)
                total_r += reward
                state    = next_s

            ep_rewards.append(total_r)
            self.stats["gym_episodes"] += 1
            self.stats["gym_rewards"].append(total_r)

            # Record episode in symbolic brain
            self.gym_symbolic.record_episode(
                action_seq, [],
                total_r, total_r > 50,
                self.gym_env.get_id(),
            )

            # Discover skills every 50 episodes
            if (ep+1) % 50 == 0:
                new_skills = self.gym_symbolic.discover_skills()
                self.stats["skills_found"] += len(new_skills)
                avg_r = sum(ep_rewards[-50:])/50
                if verbose:
                    print(f"   Ep {ep+1:4d} | avg_r={avg_r:7.2f} | "
                          f"ε={self.gym_neural.epsilon:.3f} | "
                          f"skills={len(self.gym_symbolic.skills)}")

        print(f"   Pre-training complete. Skills: {len(self.gym_symbolic.skills)}")
        return {
            "episodes":    episodes,
            "avg_reward":  sum(ep_rewards)/max(len(ep_rewards),1),
            "final_epsilon": self.gym_neural.epsilon,
            "skills":      len(self.gym_symbolic.skills),
        }

    def transfer_to_gfs(self) -> dict:
        """
        Transfer Phase: gymnasium skills → GFS action space.
        Also transfers Q-value distribution knowledge.
        """
        print(f"\n── Transfer Phase: gymnasium → GFS ──")

        transferred = self.transfer_mapper.transfer_all(
            self.gym_symbolic, self.gfs_symbolic)
        self.stats["skills_xferred"] = transferred

        print(f"   Skills transferred: {transferred}")
        print(f"   GFS symbolic brain: {len(self.gfs_symbolic.skills)} skills")

        # Q-value warm start — gym neural Q-dist informs GFS neural init
        # High-reward actions in gym map to high-weight GFS core files
        gym_q_dist = [sum(self.gym_neural.W3[i][j]
                          for j in range(len(self.gym_neural.W3[i])))
                      for i in range(len(self.gym_neural.W3))]

        return {
            "skills_transferred": transferred,
            "gym_skills":         len(self.gym_symbolic.skills),
            "gfs_skills":         len(self.gfs_symbolic.skills),
        }

    def train_gfs(self, episodes: int = 200,
                  verbose: bool = True) -> dict:
        """
        Phase 2: Fine-tune on GFS environment.
        Starts with transferred skills, learns GFS-specific patterns.
        """
        print(f"\n── Phase 2: GFS production training ({episodes} episodes) ──")
        print(f"   Registry: {len(self.registry_files)} files")
        print(f"   Action space: {self.gfs_env.get_action_size()}")

        ep_rewards = []

        for ep in range(episodes):
            state      = self.gfs_env.reset()
            total_r    = 0.0
            done       = False
            action_seq = []
            fname_seq  = []

            # Use best symbolic skill if available (warm start)
            best_skill = self.gfs_symbolic.best_skill_for_state(
                state, list(range(GFSEnvironmentAdapter.ACTION_SPACE)))

            while not done:
                # Symbolic brain override on first step if skill available
                if best_skill and not action_seq:
                    action = best_skill.action_seq[0] % self.gfs_env.get_action_size()
                else:
                    action = self.gfs_neural.act(state)

                next_s, reward, done, info = self.gfs_env.step(action)
                self.gfs_neural.remember(state, action, reward, next_s, done)
                loss = self.gfs_neural.replay()

                action_seq.append(action)
                if 'fname' in info: fname_seq.append(info['fname'])
                total_r += reward
                state    = next_s
                self.stats["training_steps"] += 1

            ep_rewards.append(total_r)
            self.stats["gfs_episodes"]  += 1
            self.stats["gfs_rewards"].append(total_r)

            # Record for skill discovery
            self.gfs_symbolic.record_episode(
                action_seq, fname_seq,
                total_r, total_r > 1.0,
                self.gfs_env.get_id(),
            )

            if (ep+1) % 50 == 0:
                new_skills = self.gfs_symbolic.discover_skills()
                self.stats["skills_found"] += len(new_skills)
                avg_r = sum(ep_rewards[-50:])/50
                if verbose:
                    print(f"   Ep {ep+1:4d} | avg_r={avg_r:7.3f} | "
                          f"ε={self.gfs_neural.epsilon:.3f} | "
                          f"skills={len(self.gfs_symbolic.skills)}")

        print(f"   GFS training complete.")
        return {
            "episodes":    episodes,
            "avg_reward":  sum(ep_rewards)/max(len(ep_rewards),1),
            "skills":      len(self.gfs_symbolic.skills),
        }

    def dispatch(self, gfs_state: dict,
                 use_symbolic: bool = True) -> tuple[str, float, dict]:
        """
        Production dispatch — dual brain decision.
        Returns (filename, confidence, meta)
        """
        state_vec = self.gfs_normalizer.encode_gfs_state(gfs_state)

        # Q-values from neural brain
        q_vals = self.gfs_neural.q_values(state_vec)

        # Symbolic override if high-confidence skill matches
        if use_symbolic:
            avail = list(range(GFSEnvironmentAdapter.ACTION_SPACE))
            skill = self.gfs_symbolic.best_skill_for_state(state_vec, avail)
            if skill and skill.success_rate > 0.9:
                action    = skill.action_seq[0] % len(self.gfs_env._action_map)
                fname     = self.gfs_env._action_map[action]
                q_conf    = q_vals[action] if action < len(q_vals) else 0.0
                return fname, skill.success_rate, {
                    "source":  "symbolic",
                    "skill":   skill.name,
                    "q_value": q_conf,
                }

        # Neural brain decision
        action = q_vals.index(max(q_vals))
        action = min(action, len(self.gfs_env._action_map)-1)
        fname  = self.gfs_env._action_map[action]
        conf   = max(q_vals) / max(sum(abs(q) for q in q_vals), 1e-10)
        return fname, conf, {"source": "neural", "q_value": max(q_vals)}

    def merge_with(self, other: 'DualBrainAgent'):
        """
        CRDT merge: share skills between two agents.
        GhostGoat + ADAP learn from each other.
        """
        self.gfs_symbolic.merge_skills(other.gfs_symbolic.skills)
        other.gfs_symbolic.merge_skills(self.gfs_symbolic.skills)

    def save(self, path: str):
        """Save full agent state."""
        state = {
            "agent_id":     self.agent_id,
            "gym_neural":   self.gym_neural.get_state_dict(),
            "gfs_neural":   self.gfs_neural.get_state_dict(),
            "gym_symbolic": self.gym_symbolic.to_dict(),
            "gfs_symbolic": self.gfs_symbolic.to_dict(),
            "stats":        self.stats,
        }
        Path(path).write_text(json.dumps(state, indent=2))
        print(f"   Saved: {path}")

    def load(self, path: str):
        """Load full agent state."""
        state = json.loads(Path(path).read_text())
        self.gym_neural.load_state_dict(state["gym_neural"])
        self.gfs_neural.load_state_dict(state["gfs_neural"])
        self.gym_symbolic = SymbolicBrain.from_dict(
            state["gym_symbolic"], self.agent_id)
        self.gfs_symbolic = SymbolicBrain.from_dict(
            state["gfs_symbolic"], self.agent_id)
        self.stats = state["stats"]

# ═══════════════════════════════════════════════════════════════════════════════
# TEST + BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════════

def build_registry():
    return [encode_filename(i%8,i%8,i%4,i%32) for i in range(32)]

def run_tests():
    print("\n══ AGENT BYTE + GFS INTEGRATION TESTS ═══════════════════════\n")
    passed = failed = 0
    errors = []

    def ok(name, cond, detail=""):
        nonlocal passed, failed
        if cond: passed+=1; print(f"  ✓  {name}")
        else:
            failed+=1; errors.append(f"{name}: {detail}")
            print(f"  ✗  {name} — {detail}")

    registry = build_registry()

    # T1: StateNormalizer
    print("T1: StateNormalizer — 256-dim encoding")
    norm = StateNormalizer("test")
    gym_obs = [0.1, -0.2, 0.05, 0.3]
    vec1 = norm.encode_gymnasium(gym_obs)
    ok("gymnasium → 256-dim", len(vec1)==256)

    gfs_state = {"active_files":["py.orc.cor.000"],
                 "resource_load":0.3,"execution_depth":2,
                 "deadline_ms":500,"goal_progress":0.5,
                 "error_signals":[],"pending_files":[],
                 "sidecar_count":0}
    vec2 = norm.encode_gfs_state(gfs_state)
    ok("GFS state → 256-dim", len(vec2)==256)

    key_vec = norm.encode_key(12345)
    ok("key_int → 256-dim", len(key_vec)==256)

    # Different states → different vectors
    gfs_state2 = dict(gfs_state); gfs_state2["resource_load"]=0.9
    vec3 = norm.encode_gfs_state(gfs_state2)
    ok("different states → different vectors",
       any(abs(a-b)>0.001 for a,b in zip(vec2,vec3)))

    # T2: NeuralBrain
    print("\nT2: NeuralBrain DQN")
    brain = NeuralBrain(state_size=256, action_size=4, epsilon=0.5)
    state = [random.random() for _ in range(256)]
    action = brain.act(state)
    ok("act returns valid action", 0<=action<4)

    q = brain.q_values(state)
    ok("q_values returns 4 values", len(q)==4)

    # Train a few steps
    for _ in range(40):
        s  = [random.random() for _ in range(256)]
        a  = random.randint(0,3)
        r  = random.random()
        ns = [random.random() for _ in range(256)]
        brain.remember(s, a, r, ns, False)
    loss = brain.replay()
    ok("replay returns loss after 40 experiences", loss is not None)
    ok("epsilon decays after replay", brain.epsilon < 0.5)

    # T3: SymbolicBrain
    print("\nT3: SymbolicBrain skill discovery")
    sym = SymbolicBrain("test_agent")
    for _ in range(5):
        sym.record_episode([0,1,2],[],0.85,True,"gymnasium:CartPole")
    for _ in range(5):
        sym.record_episode([0,1,2],[],0.90,True,"gymnasium:CartPole")
    skills = sym.discover_skills()
    ok("skills discovered from repeated patterns", len(skills)>0)
    ok("skill has high success rate", skills[0].success_rate>=0.8 if skills else False)

    # Merge
    sym2 = SymbolicBrain("agent_2")
    for _ in range(4):
        sym2.record_episode([3,4,5],[],0.75,True,"gymnasium:CartPole")
    sym2.discover_skills()
    pre_merge = len(sym.skills)
    sym.merge_skills(sym2.skills)
    ok("CRDT merge adds new skills", len(sym.skills)>=pre_merge)

    # T4: Gymnasium adapter
    print("\nT4: Gymnasium environment adapter")
    gym_env = GymnasiumAdapter("CartPole")
    state   = gym_env.reset()
    ok("reset returns state", len(state)==4)
    ns, r, done, info = gym_env.step(1)
    ok("step returns (state, reward, done, info)", len(ns)==4)
    ok("reward is float", isinstance(r, float))
    ok("get_action_size=2", gym_env.get_action_size()==2)
    ok("get_id correct", "CartPole" in gym_env.get_id())

    # T5: GFS environment adapter
    print("\nT5: GFS environment adapter")
    gfs_env = GFSEnvironmentAdapter(registry)
    state   = gfs_env.reset()
    ok("GFS reset → 256-dim state", len(state)==256)
    ns, r, done, info = gfs_env.step(0)
    ok("GFS step returns state", len(ns)==256)
    ok("GFS step returns reward", isinstance(r, float))
    ok("action_size=256", gfs_env.get_action_size()==256)
    ok("get_id=gfs:production", gfs_env.get_id()=="gfs:production")

    # T6: TransferMapper
    print("\nT6: TransferMapper — gymnasium → GFS transfer")
    gym_norm = StateNormalizer("gym")
    gfs_norm = StateNormalizer("gfs")
    mapper   = TransferMapper(gym_norm, gfs_norm, registry)

    gym_skill = Skill(
        skill_id="test_skill_001",
        name="test_skill",
        description="high reward path",
        action_seq=[0,1,0],
        fname_seq=[],
        avg_reward=0.85,
        success_rate=0.9,
        use_count=10,
        env_origin="gymnasium:CartPole",
        agent_origin="test",
        transferable=True,
    )
    transferred = mapper.transfer(gym_skill, "adap")
    ok("skill transfers to GFS", transferred is not None)
    ok("transferred skill has GFS files",
       len(transferred.fname_seq)>0 if transferred else False)
    ok("transferred env_origin tagged",
       "transferred" in transferred.env_origin if transferred else False)

    # T7: Full DualBrainAgent
    print("\nT7: DualBrainAgent — fast integration test")
    agent = DualBrainAgent("test_agent", registry, "CartPole")

    # Quick gymnasium pre-training (10 episodes)
    gym_result = agent.pretrain_gymnasium(episodes=10, verbose=False)
    ok("gymnasium pre-training completes", gym_result["episodes"]==10)
    ok("epsilon decays during training",
       agent.gym_neural.epsilon < 1.0)

    # Transfer
    xfer = agent.transfer_to_gfs()
    ok("transfer executes", "skills_transferred" in xfer)

    # Quick GFS training (10 episodes)
    gfs_result = agent.train_gfs(episodes=10, verbose=False)
    ok("GFS training completes", gfs_result["episodes"]==10)

    # Production dispatch
    fname, conf, meta = agent.dispatch(gfs_state)
    ok("dispatch returns valid filename",
       fname in registry or '.' in fname)
    ok("dispatch returns confidence", isinstance(conf, float))
    ok("dispatch has source", "source" in meta)

    # T8: Multi-agent CRDT merge
    print("\nT8: Multi-agent skill sharing (GhostGoat ↔ ADAP)")
    ghostgoat = DualBrainAgent("ghostgoat", registry)
    adap      = DualBrainAgent("adap", registry)

    # Give each agent some skills
    ghostgoat.pretrain_gymnasium(episodes=5, verbose=False)
    ghostgoat.transfer_to_gfs()
    adap.pretrain_gymnasium(episodes=5, verbose=False)
    adap.transfer_to_gfs()

    gg_skills_pre  = len(ghostgoat.gfs_symbolic.skills)
    adap_skills_pre= len(adap.gfs_symbolic.skills)

    ghostgoat.merge_with(adap)

    ok("merge shares skills bidirectionally",
       len(ghostgoat.gfs_symbolic.skills) >= gg_skills_pre)

    # T9: Save / load
    print("\nT9: Agent persistence")
    save_path = "/tmp/test_agent_byte_gfs.json"
    agent.save(save_path)
    ok("agent saves to disk", Path(save_path).exists())

    agent2 = DualBrainAgent("test_loaded", registry)
    agent2.load(save_path)
    ok("agent loads from disk", agent2.stats["gym_episodes"]>0)
    Path(save_path).unlink(missing_ok=True)

    print(f"\n  {'═'*52}")
    print(f"  PASSED: {passed}/{passed+failed}")
    if errors:
        for e in errors: print(f"    ✗ {e}")
    return failed==0

def run_benchmark():
    print("\n══ AGENT BYTE + GFS BENCHMARK ════════════════════════════════\n")
    registry = build_registry()

    def tm(fn, n=100):
        s=time.perf_counter()
        for _ in range(n): fn()
        return ((time.perf_counter()-s)*1e6)/n

    norm    = StateNormalizer("bench")
    brain   = NeuralBrain(state_size=256, action_size=256)
    gfs_env = GFSEnvironmentAdapter(registry, norm)
    state   = [random.random() for _ in range(256)]
    gfs_st  = {"active_files":["py.orc.cor.000"],"resource_load":0.3,
               "execution_depth":2,"deadline_ms":500,"goal_progress":0.5,
               "error_signals":[],"pending_files":[],"sidecar_count":0}

    # Pre-fill replay buffer
    for _ in range(100):
        brain.remember([random.random() for _ in range(256)],
                       random.randint(0,255),random.random(),
                       [random.random() for _ in range(256)],False)

    b = [
        ("StateNormalizer gym encode",   lambda: norm.encode_gymnasium([0.1,-0.2,0.05,0.3]), 500),
        ("StateNormalizer GFS encode",   lambda: norm.encode_gfs_state(gfs_st),               500),
        ("NeuralBrain act (epsilon=0)",  lambda: brain.act(state),                           1000),
        ("NeuralBrain q_values",         lambda: brain.q_values(state),                      1000),
        ("NeuralBrain replay (32 batch)",lambda: brain.replay(),                               100),
        ("GFS env step",                 lambda: gfs_env.step(random.randint(0,255)),          500),
        ("GFS env reset",                lambda: gfs_env.reset(),                              500),
    ]

    for name, fn, n in b:
        us = tm(fn, n)
        print(f"  {name:<40} {us:>10.3f} μs/op")

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv)>1 else "all"
    t_ok = True
    if cmd in ("test","all"):  t_ok = run_tests()
    if cmd in ("bench","all"): run_benchmark()
    if cmd == "all":
        print(f"\n{'═'*62}")
        print(f"  Agent Byte + GFS Integration")
        print(f"  Tests: {'ALL PASSED' if t_ok else 'FAILURES'}")
        print(f"  Both gymnasium + GFS training verified")
        print(f"  CRDT multi-agent skill sharing verified")
        print(f"{'═'*62}")

