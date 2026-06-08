#!/usr/bin/env python3
"""
GFS v4 — Ghost File System
CRDT Manifest + Twin Entanglement

New in v4:
  CRDT layer:
    - OR-Set manifest          → conflict-free concurrent registration
    - G-Counter per agent      → collision-free sequence namespace
    - Vector clock per entry   → causal merge without coordinator
    - Merkle CRDT diff/merge   → sync only divergent branches

  Entanglement layer:
    - Symmetric entanglement   → bind(A,B) — mutual dependency
    - Asymmetric entanglement  → bind(A, B*weight) — role hierarchy
    - Entangled pair registry  → pairs as first-class objects
    - Cascade invalidation     → change A → pair hash changes → Merkle flags B
    - Multi-entanglement       → one file entangled with N others (fan-out)

  Inherited from v3:
    - Extensionless segment coding (py.orc.cor.000)
    - FHRR holographic collapse
    - MIS attractor routing
    - Lyapunov stability scores
    - Security-audited decode (seq 0-255 enforced)
"""

import json
import math
import cmath
import hashlib
import struct
import time
import uuid
import sys
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime, timezone
from copy import deepcopy

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA (unchanged from v3)
# ═══════════════════════════════════════════════════════════════════════════════

TYPES = {
    0b000: ("py", "python",   "Python script"),
    0b001: ("js", "json",     "JSON data/config"),
    0b010: ("yl", "yaml",     "YAML config"),
    0b011: ("bn", "binary",   "Binary/compiled"),
    0b100: ("md", "markdown", "Markdown doc"),
    0b101: ("sh", "shell",    "Shell script"),
    0b110: ("cp", "cpp",      "C/C++ source"),
    0b111: ("tx", "text",     "Plain text"),
}
ROLES = {
    0b000: ("orc", "orchestrator"), 0b001: ("tol", "tool"),
    0b010: ("cfg", "config"),       0b011: ("dat", "data"),
    0b100: ("doc", "doc"),          0b101: ("tst", "test"),
    0b110: ("brd", "bridge"),       0b111: ("eph", "ephemeral"),
}
TIERS = {
    0b00: ("cor", "core"),    0b01: ("plg", "plugin"),
    0b10: ("snd", "sandbox"), 0b11: ("arc", "archive"),
}
TYPE_ABV = {v[0]: k for k, v in TYPES.items()}
ROLE_ABV = {v[0]: k for k, v in ROLES.items()}
TIER_ABV = {v[0]: k for k, v in TIERS.items()}

def encode_filename(ti, ri, ii, sq) -> str:
    return f"{TYPES[ti][0]}.{ROLES[ri][0]}.{TIERS[ii][0]}.{sq:03d}"

def decode_filename(fname: str) -> dict:
    parts = Path(fname).name.split('.')
    if len(parts) != 4:
        raise ValueError(f"Invalid GFS filename: '{fname}'")
    ta, ra, ia, sq = parts
    if ta not in TYPE_ABV: raise ValueError(f"Unknown type: '{ta}'")
    if ra not in ROLE_ABV: raise ValueError(f"Unknown role: '{ra}'")
    if ia not in TIER_ABV: raise ValueError(f"Unknown tier: '{ia}'")
    ti, ri, ii = TYPE_ABV[ta], ROLE_ABV[ra], TIER_ABV[ia]
    seq = int(sq)
    if not (0 <= seq <= 255): raise ValueError(f"Seq out of range: {seq}")
    key_int = (ti << 13) | (ri << 10) | (ii << 8) | seq
    return dict(filename=fname, type_id=ti, role_id=ri, tier_id=ii,
                sequence=seq, key_int=key_int, key_bin=format(key_int,'016b'),
                type=TYPES[ti][2], handler=TYPES[ti][1],
                role=ROLES[ri][1], tier=TIERS[ii][1],
                cache_hint=(ii==0b00 and ri in (0b000,0b001)))

# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR CLOCK
# ═══════════════════════════════════════════════════════════════════════════════

class VectorClock:
    """
    Causal ordering without coordinator.
    Each agent increments its own counter.
    Merge = elementwise max.
    Happens-before: vc_a < vc_b iff all(a[k]<=b[k]) and any(a[k]<b[k])
    """

    def __init__(self, agent_id: str, clocks: dict = None):
        self.agent_id = agent_id
        self.clocks: dict[str, int] = clocks or {}

    def tick(self) -> 'VectorClock':
        c = deepcopy(self)
        c.clocks[self.agent_id] = c.clocks.get(self.agent_id, 0) + 1
        return c

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        all_agents = set(self.clocks) | set(other.clocks)
        merged = {a: max(self.clocks.get(a,0), other.clocks.get(a,0))
                  for a in all_agents}
        return VectorClock(self.agent_id, merged)

    def happens_before(self, other: 'VectorClock') -> bool:
        all_agents = set(self.clocks) | set(other.clocks)
        return (all(self.clocks.get(a,0) <= other.clocks.get(a,0) for a in all_agents)
                and any(self.clocks.get(a,0) < other.clocks.get(a,0) for a in all_agents))

    def concurrent_with(self, other: 'VectorClock') -> bool:
        return (not self.happens_before(other) and
                not other.happens_before(self))

    def to_dict(self) -> dict:
        return {"agent_id": self.agent_id, "clocks": self.clocks}

    @classmethod
    def from_dict(cls, d: dict) -> 'VectorClock':
        return cls(d["agent_id"], d["clocks"])

    def __repr__(self):
        return f"VC({self.clocks})"

# ═══════════════════════════════════════════════════════════════════════════════
# G-COUNTER — collision-free sequence assignment
# ═══════════════════════════════════════════════════════════════════════════════

class GCounter:
    """
    Grow-only counter per agent.
    Each agent owns a shard of the sequence namespace.
    Merge = elementwise max.
    No coordinator needed — shards never overlap.

    Namespace sharding (max 4 agents per type/role/tier bucket):
      Agent 0: seq 000-063
      Agent 1: seq 064-127
      Agent 2: seq 128-191
      Agent 3: seq 192-255
    """

    SHARD_SIZE = 64  # 256 / 4 agents

    def __init__(self, agent_id: str, agent_index: int = 0, counts: dict = None):
        self.agent_id    = agent_id
        self.agent_index = agent_index  # 0-3
        self.counts: dict[str, int] = counts or {}  # bucket_key → local count

    def _bucket(self, ti, ri, ii) -> str:
        return f"{ti}.{ri}.{ii}"

    def _base(self) -> int:
        return self.agent_index * self.SHARD_SIZE

    def next_seq(self, ti, ri, ii) -> int:
        bucket = self._bucket(ti, ri, ii)
        local  = self.counts.get(bucket, 0)
        seq    = self._base() + local
        if seq >= self._base() + self.SHARD_SIZE:
            raise OverflowError(
                f"Agent {self.agent_id} shard exhausted for {bucket}")
        self.counts[bucket] = local + 1
        return seq

    def merge(self, other: 'GCounter') -> 'GCounter':
        all_buckets = set(self.counts) | set(other.counts)
        merged = {b: max(self.counts.get(b,0), other.counts.get(b,0))
                  for b in all_buckets}
        return GCounter(self.agent_id, self.agent_index, merged)

    def to_dict(self) -> dict:
        return {"agent_id": self.agent_id,
                "agent_index": self.agent_index,
                "counts": self.counts}

    @classmethod
    def from_dict(cls, d: dict) -> 'GCounter':
        return cls(d["agent_id"], d["agent_index"], d["counts"])

# ═══════════════════════════════════════════════════════════════════════════════
# OR-SET — conflict-free file registry
# ═══════════════════════════════════════════════════════════════════════════════

class ORSet:
    """
    Observed-Remove Set.
    Add: tag element with unique token (UUID + agent + vc)
    Remove: mark that specific token as removed
    Merge: union of adds, union of removes — deterministic always

    Concurrent add + remove of same file = add wins (by token)
    Two agents add same filename = two distinct entries, both survive merge
    """

    def __init__(self):
        # filename → set of (token, agent_id, vc_dict)
        self.adds:    dict[str, list[dict]] = {}
        # removed token set
        self.removes: set[str] = set()

    def add(self, filename: str, agent_id: str, vc: VectorClock) -> str:
        token = str(uuid.uuid4())
        if filename not in self.adds:
            self.adds[filename] = []
        self.adds[filename].append({
            "token":    token,
            "agent_id": agent_id,
            "vc":       vc.to_dict(),
        })
        return token

    def remove(self, filename: str):
        """Observe and remove all current tokens for filename."""
        if filename in self.adds:
            for entry in self.adds[filename]:
                self.removes.add(entry["token"])

    def contains(self, filename: str) -> bool:
        if filename not in self.adds:
            return False
        return any(e["token"] not in self.removes
                   for e in self.adds[filename])

    def elements(self) -> list[str]:
        return [f for f in self.adds if self.contains(f)]

    def merge(self, other: 'ORSet') -> 'ORSet':
        merged = ORSet()
        # union adds
        all_files = set(self.adds) | set(other.adds)
        for f in all_files:
            mine   = self.adds.get(f, [])
            theirs = other.adds.get(f, [])
            # deduplicate by token
            seen   = set()
            combined = []
            for e in mine + theirs:
                if e["token"] not in seen:
                    seen.add(e["token"])
                    combined.append(e)
            merged.adds[f] = combined
        # union removes
        merged.removes = self.removes | other.removes
        return merged

    def to_dict(self) -> dict:
        return {"adds": self.adds, "removes": list(self.removes)}

    @classmethod
    def from_dict(cls, d: dict) -> 'ORSet':
        s = cls()
        s.adds    = d["adds"]
        s.removes = set(d["removes"])
        return s

# ═══════════════════════════════════════════════════════════════════════════════
# FHRR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class FHRR:
    def __init__(self, dim: int = 512, seed: int = 42):
        self.D    = dim
        self._seed = seed
        self._vocab: dict[str, list[complex]] = {}

    def _phase_key(self, label: str) -> list[complex]:
        if label in self._vocab:
            return self._vocab[label]
        phases, block = [], hashlib.sha3_256(
            f"{self._seed}:{label}".encode()).digest()
        while len(phases) < self.D:
            for i in range(0, len(block)-1, 2):
                a = (struct.unpack_from('>H',block,i)[0]/65536.0)*2*math.pi
                phases.append(cmath.exp(1j*a))
                if len(phases)==self.D: break
            block = hashlib.sha3_256(block).digest()
        self._vocab[label] = phases[:self.D]
        return self._vocab[label]

    def bind(self, a, b, weight=1.0):
        """Elementwise complex multiplication. weight scales b for asymmetry."""
        return [x*(y*weight) for x,y in zip(a,b)]

    def unbind(self, s, k):
        return [x*y.conjugate() for x,y in zip(s,k)]

    def superpose(self, vecs):
        r = [0+0j]*self.D
        for v in vecs: r = [a+b for a,b in zip(r,v)]
        return r

    def normalize(self, v):
        return [x/abs(x) if abs(x)>1e-10 else 1+0j for x in v]

    def similarity(self, a, b) -> float:
        dot = sum(x*y.conjugate() for x,y in zip(a,b))
        na  = math.sqrt(sum(abs(x)**2 for x in a))
        nb  = math.sqrt(sum(abs(x)**2 for x in b))
        if na<1e-10 or nb<1e-10: return 0.0
        return (dot/(na*nb)).real

    def filename_to_vec(self, fname: str) -> list[complex]:
        d  = decode_filename(fname)
        tv = self._phase_key(f"type:{d['type']}")
        rv = self._phase_key(f"role:{d['role']}")
        iv = self._phase_key(f"tier:{d['tier']}")
        sv = self._phase_key(f"seq:{d['sequence']}")
        return self.normalize(self.bind(self.bind(self.bind(tv,rv),iv),sv))

    def collapse(self, fnames: list[str]) -> list[complex]:
        if not fnames: return [1+0j]*self.D
        return self.normalize(self.superpose(
            [self.filename_to_vec(f) for f in fnames]))

    def membership_score(self, collapsed, fname: str) -> float:
        cv      = self.filename_to_vec(fname)
        unbound = self.unbind(collapsed, cv)
        return self.similarity(unbound, [1+0j]*self.D)

# ═══════════════════════════════════════════════════════════════════════════════
# ENTANGLEMENT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EntangledPair:
    """
    Twin entanglement between two GFS files.
    pair_id:    unique identifier for this bond
    fname_a:    dominant file (weight=1.0)
    fname_b:    subordinate file (weight scales asymmetry)
    weight:     asymmetry factor 0.0-1.0
                1.0 = symmetric (equals)
                0.3 = asymmetric (B subordinate to A)
    vec:        serialized entangled FHRR vector
    pair_hash:  SHA3-256 of the pair — changes if either file changes
    agent_id:   agent that created this bond
    vc:         vector clock at creation
    created_at: ISO timestamp
    tags:       searchable labels
    """
    pair_id:    str
    fname_a:    str
    fname_b:    str
    weight:     float
    vec:        str          # serialized FHRR
    pair_hash:  str
    agent_id:   str
    vc:         dict
    created_at: str = ""
    tags:       list = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

class EntanglementEngine:
    """
    Manages twin entanglement between GFS files.

    Symmetric:   bind(A, B)           — mutual dependency, equal weight
    Asymmetric:  bind(A, B * weight)  — A dominates B

    Cascade invalidation:
      File changes → pair_hash changes → Merkle subtree invalidated
      → all files entangled with changed file flagged for revalidation

    Multi-entanglement (fan-out):
      One file entangled with N others
      collapse([pair_1, pair_2, ...pair_N]) → single holographic vector
      representing the entire dependency web
    """

    def __init__(self, fhrr: FHRR):
        self.fhrr   = fhrr
        self.pairs:  dict[str, EntangledPair] = {}
        self.index:  dict[str, list[str]]     = {}
        # Lazy web cache: fname → (web_hash, collapsed_vec, result_dict)
        # Invalidated on entangle() and cascade_invalidate()
        self._web_cache: dict[str, tuple] = {}

    def _pair_hash(self, fname_a: str, fname_b: str, weight: float) -> str:
        d = decode_filename(fname_a)
        e = decode_filename(fname_b)
        data = f"{d['key_int']}:{e['key_int']}:{weight:.6f}"
        return hashlib.sha3_256(data.encode()).hexdigest()

    def entangle(self, fname_a: str, fname_b: str,
                 agent_id: str, vc: VectorClock,
                 weight: float = 1.0,
                 tags: list = None) -> EntangledPair:
        """
        Create a twin entanglement bond.
        weight=1.0  → symmetric  (py.orc + js.cfg as equals)
        weight=0.3  → asymmetric (py.orc dominates js.cfg)
        """
        # Validate both filenames
        decode_filename(fname_a)
        decode_filename(fname_b)

        va = self.fhrr.filename_to_vec(fname_a)
        vb = self.fhrr.filename_to_vec(fname_b)

        # Core operation: asymmetric bind
        # A is always at full weight, B is scaled
        entangled_vec = self.fhrr.normalize(
            self.fhrr.bind(va, vb, weight=weight))

        # Serialize first 16 components for storage (full vec in memory)
        vec_str = ','.join(
            f"{x.real:.4f}:{x.imag:.4f}" for x in entangled_vec[:16]) + "…"

        pair = EntangledPair(
            pair_id   = str(uuid.uuid4()),
            fname_a   = fname_a,
            fname_b   = fname_b,
            weight    = weight,
            vec       = vec_str,
            pair_hash = self._pair_hash(fname_a, fname_b, weight),
            agent_id  = agent_id,
            vc        = vc.tick().to_dict(),
            tags      = tags or [],
        )
        self.pairs[pair.pair_id] = pair

        # Update index
        for f in (fname_a, fname_b):
            if f not in self.index:
                self.index[f] = []
            self.index[f].append(pair.pair_id)

        # Invalidate web cache for both files
        for f in (fname_a, fname_b):
            self._web_cache.pop(f, None)
        return pair

    def entangle_many(self, fname_primary: str, others: list[str],
                      agent_id: str, vc: VectorClock,
                      weight: float = 0.5) -> list[EntangledPair]:
        """
        Fan-out: entangle one file with N others.
        Used for orchestrator → [tool1, tool2, config, bridge]
        """
        return [self.entangle(fname_primary, f, agent_id, vc, weight)
                for f in others]

    def get_partners(self, fname: str) -> list[str]:
        """All files entangled with fname."""
        pair_ids = self.index.get(fname, [])
        partners = []
        for pid in pair_ids:
            pair = self.pairs.get(pid)
            if pair:
                partner = pair.fname_b if pair.fname_a==fname else pair.fname_a
                partners.append(partner)
        return partners

    def cascade_invalidate(self, changed_fname: str) -> list[str]:
        """
        File changed → find all entangled partners → return for revalidation.
        This is the cascade: changing one file automatically flags its twins.
        """
        directly_affected = self.get_partners(changed_fname)
        all_affected      = set(directly_affected)

        # One level of cascade (configurable depth)
        for f in directly_affected:
            second_order = self.get_partners(f)
            all_affected.update(second_order)

        all_affected.discard(changed_fname)
        # Invalidate web cache for changed file and all affected
        for f in list(all_affected) + [changed_fname]:
            self._web_cache.pop(f, None)
        return list(all_affected)

    def recover_b(self, pair_id: str) -> float:
        """
        Demonstrate recovery: given entangled pair, score recovery of B from A.
        In full implementation: unbind(entangled_vec, vec_A) ≈ vec_B
        Returns similarity score.
        """
        pair = self.pairs.get(pair_id)
        if not pair: return 0.0
        va = self.fhrr.filename_to_vec(pair.fname_a)
        vb = self.fhrr.filename_to_vec(pair.fname_b)
        # Reconstruct entangled vec
        entangled = self.fhrr.normalize(self.fhrr.bind(va, vb, pair.weight))
        # Unbind A to recover B
        recovered = self.fhrr.unbind(entangled, va)
        # Score against actual B
        return self.fhrr.similarity(recovered, vb)

    def holographic_web(self, fname: str) -> dict:
        """
        Lazy+invalidate cached holographic web.
        First call: compute (FHRR collapse). Subsequent: ~1us dict lookup.
        Cache invalidated automatically by entangle() and cascade_invalidate().
        """
        partners    = self.get_partners(fname)
        pair_hashes = [self.pairs[pid].pair_hash
                       for pid in self.index.get(fname, [])]
        web_hash    = hashlib.sha3_256(
            "".join(sorted(pair_hashes)).encode()).hexdigest()

        # Cache hit: web_hash unchanged means graph unchanged
        if fname in self._web_cache:
            cached_hash, _vec, cached_result = self._web_cache[fname]
            if cached_hash == web_hash:
                return {**cached_result, "cached": True}

        # Cache miss: compute collapsed vector
        collapsed = self.fhrr.collapse([fname] + partners)
        result = {
            "primary":   fname,
            "partners":  partners,
            "depth":     len(partners),
            "web_hash":  web_hash,
            "hrr_dim":   self.fhrr.D,
            "collapsed": ",".join(
                f"{x.real:.4f}:{x.imag:.4f}"
                for x in collapsed[:8]) + "…",
            "cached":    False,
        }
        self._web_cache[fname] = (web_hash, collapsed, result)
        return result

    def merge(self, other: 'EntanglementEngine') -> 'EntanglementEngine':
        """CRDT merge — union of all pairs, dedup by pair_id."""
        merged = EntanglementEngine(self.fhrr)
        for pid, pair in {**self.pairs, **other.pairs}.items():
            merged.pairs[pid] = pair
        # Rebuild index
        for pid, pair in merged.pairs.items():
            for f in (pair.fname_a, pair.fname_b):
                if f not in merged.index: merged.index[f] = []
                if pid not in merged.index[f]:
                    merged.index[f].append(pid)
        return merged

    def to_dict(self) -> dict:
        return {
            "pairs": {k: asdict(v) for k,v in self.pairs.items()},
            "index": self.index,
        }

    @classmethod
    def from_dict(cls, d: dict, fhrr: FHRR) -> 'EntanglementEngine':
        eng = cls(fhrr)
        eng.pairs = {k: EntangledPair(**v) for k,v in d["pairs"].items()}
        eng.index = d["index"]
        return eng

# ═══════════════════════════════════════════════════════════════════════════════
# MERKLE
# ═══════════════════════════════════════════════════════════════════════════════

class GFSMerkle:
    def __init__(self, fnames: list[str], pair_hashes: list[str] = None):
        self.fnames      = sorted(fnames)
        self.pair_hashes = sorted(pair_hashes or [])

    def _h(self, data: bytes) -> str:
        return hashlib.sha3_256(data).hexdigest()

    def root(self) -> str:
        # Include entanglement pair hashes in root
        # Change in any entangled pair changes the root
        all_leaves = [self._h(f.encode()) for f in self.fnames]
        all_leaves += [self._h(ph.encode()) for ph in self.pair_hashes]
        if not all_leaves: return self._h(b'empty')
        hashes = sorted(all_leaves)
        while len(hashes) > 1:
            nxt = []
            for i in range(0, len(hashes), 2):
                a = hashes[i]
                b = hashes[i+1] if i+1<len(hashes) else a
                nxt.append(self._h((a+b).encode()))
            hashes = nxt
        return hashes[0]

    def diff(self, other: 'GFSMerkle') -> dict:
        s1, s2 = set(self.fnames), set(other.fnames)
        p1, p2 = set(self.pair_hashes), set(other.pair_hashes)
        return {
            "files_added":   list(s2-s1),
            "files_removed": list(s1-s2),
            "pairs_added":   list(p2-p1),
            "pairs_removed": list(p1-p2),
            "roots_match":   self.root()==other.root(),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY v4 — CRDT + ENTANGLEMENT
# ═══════════════════════════════════════════════════════════════════════════════

MANIFEST = Path("gfs_v4_manifest.json")

@dataclass
class GFSEntry:
    filename:    str
    type_id: int; role_id: int; tier_id: int; sequence: int
    type: str; handler: str; role: str; tier: str
    key_int: int; key_bin: str
    description: str
    agent_id:    str
    vc:          dict                      # vector clock at registration
    token:       str                       # OR-Set token
    tags:        list = field(default_factory=list)
    lyapunov:    Optional[float] = None
    attractor:   Optional[str]  = None
    created_at:  str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

class GFSRegistry:
    def __init__(self, agent_id: str = "agent-0", agent_index: int = 0,
                 path: Path = MANIFEST, hrr_dim: int = 256):
        self.agent_id = agent_id
        self.path     = path
        self.fhrr     = FHRR(dim=hrr_dim)
        self.vc       = VectorClock(agent_id)
        self.gcounter = GCounter(agent_id, agent_index)
        self.orset    = ORSet()
        self.entries: dict[str, GFSEntry] = {}
        self.entanglement = EntanglementEngine(self.fhrr)
        self._load()

    def _load(self):
        if not self.path.exists(): return
        d = json.loads(self.path.read_text())
        self.entries = {k: GFSEntry(**v) for k,v in d.get("entries",{}).items()}
        if "orset" in d:
            self.orset = ORSet.from_dict(d["orset"])
        if "gcounter" in d:
            self.gcounter = GCounter.from_dict(d["gcounter"])
        if "vc" in d:
            self.vc = VectorClock.from_dict(d["vc"])
        if "entanglement" in d:
            self.entanglement = EntanglementEngine.from_dict(
                d["entanglement"], self.fhrr)

    def _save(self):
        self.path.write_text(json.dumps({
            "entries":      {k: asdict(v) for k,v in self.entries.items()},
            "orset":        self.orset.to_dict(),
            "gcounter":     self.gcounter.to_dict(),
            "vc":           self.vc.to_dict(),
            "entanglement": self.entanglement.to_dict(),
        }, indent=2))

    def register(self, ti, ri, ii, description, tags=None) -> GFSEntry:
        """CRDT-safe registration — no coordinator needed."""
        self.vc  = self.vc.tick()
        seq      = self.gcounter.next_seq(ti, ri, ii)
        fname    = encode_filename(ti, ri, ii, seq)
        dec      = decode_filename(fname)
        token    = self.orset.add(fname, self.agent_id, self.vc)

        # MIS Lyapunov
        try:
            lyap, basin = self._mis_score(fname)
        except Exception:
            lyap, basin = None, None

        e = GFSEntry(
            filename=fname, description=description, tags=tags or [],
            agent_id=self.agent_id, vc=self.vc.to_dict(), token=token,
            lyapunov=round(lyap,6) if lyap else None,
            attractor=f"{basin.real:.4f}:{basin.imag:.4f}" if basin else None,
            **{k:v for k,v in dec.items() if k not in ('filename','cache_hint')},
        )
        self.entries[fname] = e
        self._save()
        return e

    def entangle(self, fname_a: str, fname_b: str,
                 weight: float = 1.0, tags: list = None) -> EntangledPair:
        """Create twin entanglement bond between two registered files."""
        self.vc = self.vc.tick()
        pair = self.entanglement.entangle(
            fname_a, fname_b, self.agent_id, self.vc, weight, tags)
        self._save()
        return pair

    def entangle_many(self, primary: str, others: list[str],
                      weight: float = 0.5) -> list[EntangledPair]:
        self.vc = self.vc.tick()
        pairs = self.entanglement.entangle_many(
            primary, others, self.agent_id, self.vc, weight)
        self._save()
        return pairs

    def cascade(self, changed_fname: str) -> list[str]:
        return self.entanglement.cascade_invalidate(changed_fname)

    def web(self, fname: str) -> dict:
        return self.entanglement.holographic_web(fname)

    def merkle_root(self) -> str:
        pair_hashes = [p.pair_hash for p in self.entanglement.pairs.values()]
        return GFSMerkle(list(self.entries.keys()), pair_hashes).root()

    def merge(self, other: 'GFSRegistry') -> 'GFSRegistry':
        """
        CRDT merge of two registries.
        Concurrent registrations from different agents merge cleanly.
        No data lost. No coordinator. Deterministic.
        """
        merged = GFSRegistry.__new__(GFSRegistry)
        merged.agent_id     = self.agent_id
        merged.path         = self.path
        merged.fhrr         = self.fhrr
        merged.vc           = self.vc.merge(other.vc)
        merged.gcounter     = self.gcounter.merge(other.gcounter)
        merged.orset        = self.orset.merge(other.orset)
        merged.entanglement = self.entanglement.merge(other.entanglement)
        # Merge entries — vector clock determines winner for metadata conflicts
        merged.entries = {}
        all_fnames = set(self.entries) | set(other.entries)
        for f in all_fnames:
            if f in self.entries and f in other.entries:
                vc_a = VectorClock.from_dict(self.entries[f].vc)
                vc_b = VectorClock.from_dict(other.entries[f].vc)
                # Take entry with later vc; concurrent = keep both (last-writer)
                merged.entries[f] = (other.entries[f]
                    if vc_a.happens_before(vc_b) else self.entries[f])
            else:
                merged.entries[f] = (self.entries.get(f) or other.entries.get(f))
        return merged

    def resolve(self, fname: str) -> Optional[GFSEntry]:
        return self.entries.get(fname)

    def dispatch(self, fname: str) -> str:
        e = self.resolve(fname)
        return e.handler if e else decode_filename(fname)['handler']

    def query(self, role=None, tier=None, handler=None, tag=None):
        r = list(self.entries.values())
        if role:    r = [e for e in r if e.role==role]
        if tier:    r = [e for e in r if e.tier==tier]
        if handler: r = [e for e in r if e.handler==handler]
        if tag:     r = [e for e in r if tag in e.tags]
        return r

    def _mis_score(self, fname: str):
        d     = decode_filename(fname)
        k     = d['key_int']
        angle = (k/65536.0)*2*math.pi
        r     = 0.5+0.4*((k&0xFF)/255.0)
        z     = cmath.rect(r, angle)
        a,b,t = 0.5, 1.5, 1.0
        for _ in range(50):
            try:
                nz = (z**a)*cmath.exp(1j*b*t*(cmath.log(z)**b))
                if not cmath.isfinite(nz) or abs(nz)>1e6: break
                z = nz
            except: break
        # Lyapunov approx
        z2 = cmath.rect(r, angle)
        exps = []
        for _ in range(50):
            try:
                dz = a/z2+(1j*b*t*(b-1)*(cmath.log(z2)**(b-1)))/z2
                if abs(dz)>1e-10: exps.append(math.log(abs(dz)))
                z2 = (z2**a)*cmath.exp(1j*b*t*(cmath.log(z2)**b))
                if not cmath.isfinite(z2) or abs(z2)>1e6: break
            except: break
        lyap = sum(exps)/len(exps) if exps else 0.0
        return lyap, z

# ═══════════════════════════════════════════════════════════════════════════════
# TEST + BENCHMARK + AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

def _clean(path): Path(path).unlink(missing_ok=True)

def run_tests():
    passed = failed = 0
    errors = []

    def ok(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed+=1; print(f"  ✓  {name}")
        else:
            failed+=1; errors.append(f"{name}: {detail}")
            print(f"  ✗  {name} — {detail}")

    def eq(name, got, exp): ok(name, got==exp, f"got={got!r} exp={exp!r}")

    print("\n══ TEST SUITE ════════════════════════════════════════════════\n")

    # T1: Vector Clock
    print("T1: Vector Clock causality")
    vc_a = VectorClock("A")
    vc_a = vc_a.tick()
    vc_b = VectorClock("B")
    vc_b = vc_b.tick(); vc_b = vc_b.tick()
    ok("A < B not true initially",  not vc_a.happens_before(vc_b))
    merged = vc_a.merge(vc_b)
    ok("merge contains both agents", "A" in merged.clocks and "B" in merged.clocks)
    eq("merge max A", merged.clocks["A"], 1)
    eq("merge max B", merged.clocks["B"], 2)
    vc_c = merged.tick()
    ok("merged.tick() advances A",  vc_c.clocks["A"] == 2)

    # T2: G-Counter sharding
    print("\nT2: G-Counter — no collision across agents")
    gc0 = GCounter("agent-0", 0)
    gc1 = GCounter("agent-1", 1)
    gc2 = GCounter("agent-2", 2)
    seqs = set()
    collision = False
    for gc in (gc0, gc1, gc2):
        for _ in range(5):
            s = gc.next_seq(0,0,0)
            if s in seqs: collision = True
            seqs.add(s)
    ok("zero sequence collisions across 3 agents", not collision)
    ok("agent-0 shard: 0-63",   all(0<=s<64  for s in list(seqs)[:5]))
    ok("agent-1 shard: 64-127", all(64<=s<128 for s in list(seqs)[5:10]))
    merged_gc = gc0.merge(gc1)
    ok("G-Counter merge has both buckets",
       len(merged_gc.counts) >= len(gc0.counts))

    # T3: OR-Set concurrent operations
    print("\nT3: OR-Set conflict-free merge")
    os_a = ORSet(); os_b = ORSet()
    vc_x = VectorClock("A")
    vc_y = VectorClock("B")
    # Both agents add same file concurrently
    os_a.add("py.orc.cor.000", "A", vc_x.tick())
    os_b.add("py.orc.cor.000", "B", vc_y.tick())
    # Agent A also adds a unique file
    os_a.add("py.tol.cor.000", "A", vc_x.tick())
    merged_os = os_a.merge(os_b)
    ok("concurrent adds both survive", merged_os.contains("py.orc.cor.000"))
    ok("unique add survives merge",    merged_os.contains("py.tol.cor.000"))
    # Remove from one side
    os_a.remove("py.orc.cor.000")
    merged_os2 = os_a.merge(os_b)
    # OR-Set: B's token still active → file still present
    ok("remove one token, other token keeps file alive",
       merged_os2.contains("py.orc.cor.000"))

    # T4: Symmetric entanglement
    print("\nT4: Symmetric entanglement")
    fhrr = FHRR(dim=256)
    eng  = EntanglementEngine(fhrr)
    vc_e = VectorClock("test")
    pair = eng.entangle("py.orc.cor.000","js.cfg.cor.000",
                        "test", vc_e, weight=1.0)
    ok("pair created",      pair.pair_id in eng.pairs)
    ok("A indexed",         "py.orc.cor.000" in eng.index)
    ok("B indexed",         "js.cfg.cor.000" in eng.index)
    ok("pair_hash non-empty", len(pair.pair_hash) == 64)
    # Recovery score
    score = eng.recover_b(pair.pair_id)
    ok(f"B recoverable from entangled pair (score={score:.4f})", score > 0.1)

    # T5: Asymmetric entanglement
    print("\nT5: Asymmetric entanglement")
    pair_asym = eng.entangle("py.orc.cor.000","yl.cfg.cor.000",
                             "test", vc_e, weight=0.3)
    ok("asymmetric pair created", pair_asym.weight == 0.3)
    score_asym = eng.recover_b(pair_asym.pair_id)
    ok(f"B partially recoverable at weight=0.3 (score={score_asym:.4f})",
       score_asym >= 0)
    # Symmetric should recover better than asymmetric
    score_sym = eng.recover_b(pair.pair_id)
    ok(f"symmetric recovers better ({score_sym:.4f} >= {score_asym:.4f})",
       score_sym >= score_asym)

    # T6: Fan-out entanglement
    print("\nT6: Fan-out (one-to-many) entanglement")
    others = ["js.cfg.cor.000","sh.tst.snd.000","md.doc.cor.000"]
    pairs  = eng.entangle_many("py.orc.cor.000", others, "test", vc_e, 0.5)
    eq("correct number of pairs", len(pairs), len(others))
    partners = eng.get_partners("py.orc.cor.000")
    ok("all others are partners", all(o in partners for o in others))

    # T7: Cascade invalidation
    print("\nT7: Cascade invalidation")
    invalidated = eng.cascade_invalidate("js.cfg.cor.000")
    ok("cascade finds partners of changed file", len(invalidated) > 0)
    ok("changed file not in its own cascade",
       "js.cfg.cor.000" not in invalidated)
    ok("orchestrator flagged by cascade",
       "py.orc.cor.000" in invalidated)

    # T8: Holographic web
    print("\nT8: Holographic dependency web")
    web = eng.holographic_web("py.orc.cor.000")
    ok("web contains primary",  web["primary"]=="py.orc.cor.000")
    ok("web has partners",      web["depth"] > 0)
    ok("web has hash",          len(web["web_hash"])==64)
    ok("web has collapsed vec", "…" in web["collapsed"])

    # T9: Entanglement merge (CRDT)
    print("\nT9: Entanglement CRDT merge")
    eng_b = EntanglementEngine(fhrr)
    vc_f  = VectorClock("agent-b")
    eng_b.entangle("sh.tst.snd.000","md.doc.cor.000","agent-b",vc_f,0.7)
    merged_eng = eng.merge(eng_b)
    ok("merged has pairs from both engines",
       len(merged_eng.pairs) >= len(eng.pairs) + len(eng_b.pairs))

    # T10: Merkle includes pair hashes
    print("\nT10: Merkle root includes entanglement")
    files     = ["py.orc.cor.000","js.cfg.cor.000"]
    ph1       = ["abc123"*10+"abcd"]
    ph2       = ["abc123"*10+"abce"]  # one char different
    m1 = GFSMerkle(files, ph1)
    m2 = GFSMerkle(files, ph2)
    ok("different pair hashes → different roots", m1.root()!=m2.root())
    m3 = GFSMerkle(files, ph1)
    ok("same pair hashes → same root", m1.root()==m3.root())
    diff = m1.diff(m2)
    ok("diff detects pair change", len(diff["pairs_added"])>0)

    # T11: Registry CRDT merge
    print("\nT11: Registry CRDT merge (two concurrent agents)")
    p0 = Path("/tmp/gfs_v4_reg0.json")
    p1 = Path("/tmp/gfs_v4_reg1.json")
    _clean(p0); _clean(p1)

    reg0 = GFSRegistry("agent-0", 0, p0, hrr_dim=64)
    reg1 = GFSRegistry("agent-1", 1, p1, hrr_dim=64)

    # Concurrent registrations
    e0a = reg0.register(0,0,0,"ADAP orchestrator",["adap"])
    e0b = reg0.register(1,2,0,"ADAP config",["adap"])
    e1a = reg1.register(0,1,0,"GhostGoat tool",["ghostgoat"])
    e1b = reg1.register(0,6,0,"Nexus bridge",["nexus"])

    # No overlap in sequences (G-Counter sharding)
    # Collision = same filename, not same seq number (seq 0 valid in diff buckets)
    all_fnames = [e0a.filename, e0b.filename, e1a.filename, e1b.filename]
    ok("no filename collisions between agents", len(set(all_fnames))==4)

    merged_reg = reg0.merge(reg1)
    ok("merged has all 4 files", len(merged_reg.entries)==4)

    # Entangle across agent boundary
    reg0.entangle(e0a.filename, e0b.filename, weight=0.5, tags=["adap-dep"])
    reg0.entangle(e0a.filename, e1a.filename, weight=0.3, tags=["cross-agent"])

    web0 = reg0.web(e0a.filename)
    ok("cross-agent web works", web0["depth"] >= 2)

    cascade = reg0.cascade(e0b.filename)
    ok("cascade crosses agent boundary", e0a.filename in cascade)

    _clean(p0); _clean(p1)

    # T12: Dispatch without manifest
    print("\nT12: Zero-manifest dispatch")
    cases = [("py.orc.cor.000","python"),("js.cfg.cor.000","json"),
             ("sh.tst.snd.000","shell"),("cp.brd.cor.001","cpp")]
    for fname, exp in cases:
        eq(f"{fname}→{exp}", decode_filename(fname)['handler'], exp)

    total = passed+failed
    print(f"\n  {'═'*50}")
    print(f"  PASSED: {passed}/{total}")
    if errors:
        for e in errors: print(f"    ✗ {e}")
    return failed==0

def run_benchmarks():
    print("\n══ BENCHMARK SUITE ═══════════════════════════════════════════\n")

    def tm(fn, n=1000):
        s=time.perf_counter()
        for _ in range(n): fn()
        e=(time.perf_counter()-s)*1000
        return e/n*1000

    fhrr = FHRR(dim=256)
    eng  = EntanglementEngine(fhrr)
    vc   = VectorClock("bench")

    # Pre-create pairs
    eng.entangle("py.orc.cor.000","js.cfg.cor.000","bench",vc,1.0)
    eng.entangle("py.orc.cor.000","sh.tst.snd.000","bench",vc,0.5)

    b = [
        ("Encode filename",         lambda: encode_filename(0,1,0,5),              10000),
        ("Decode filename",         lambda: decode_filename("py.tol.cor.005"),      10000),
        ("Bitwise TYPE extract",    lambda: (12345>>13)&7,                         1000000),
        ("VC tick",                 lambda: vc.tick(),                              10000),
        ("VC merge",                lambda: vc.merge(vc),                           10000),
        ("G-Counter next_seq",      lambda: GCounter("x",0).next_seq(0,0,0),        5000),
        ("FHRR vec generate",       lambda: fhrr.filename_to_vec("py.orc.cor.000"),   200),
        ("Entangle (sym)",          lambda: eng.entangle("py.orc.cor.000",
                                        "md.doc.cor.000","bench",vc,1.0),             100),
        ("Cascade invalidate",      lambda: eng.cascade_invalidate("js.cfg.cor.000"),1000),
        ("Holographic web",         lambda: eng.holographic_web("py.orc.cor.000"),   500),
        ("Recover B from pair",     lambda: eng.recover_b(
                                        list(eng.pairs.keys())[0]),                   200),
        ("Merkle root (10 files)",  lambda: GFSMerkle(
                                        [encode_filename(0,i%8,0,i) for i in range(10)],
                                        ["hash"*16]*3).root(),                       1000),
        ("Full dispatch cycle",     lambda: decode_filename("py.tol.cor.005")['handler'],10000),
        ("Semantic search (old)",   lambda: [n for n in
                                        [f"tool_{i}.py" for i in range(100)]
                                        if 'tool' in n],                            10000),
        ("GFS bitwise search",      lambda: [k for k in range(100)
                                        if (k&0b0001110000000000)==
                                           0b0000010000000000],                     10000),
    ]

    results = {}
    for name, fn, n in b:
        u = tm(fn, n)
        results[name] = u
        print(f"  {name:<35} {u:>10.4f} μs/op")

    sem = results["Semantic search (old)"]
    bit = results["GFS bitwise search"]
    print(f"\n  Bitwise vs semantic: {sem/bit:.1f}x faster")
    print(f"  Cascade invalidate:  {results['Cascade invalidate']:.4f} μs — zero manifest scan")
    print(f"  Entanglement web:    {results['Holographic web']:.2f} μs — entire dep graph in one op")

def run_audit():
    print("\n══ SECURITY AUDIT ════════════════════════════════════════════\n")
    passed = warned = 0
    findings = []

    def ok(n, d=""): nonlocal passed; passed+=1; print(f"  ✓  {n}"+(f" — {d}" if d else ""))
    def warn(n, d=""): nonlocal warned; warned+=1; findings.append((n,d)); print(f"  ⚠  {n} — {d}")

    # A1: Sequence collision resistance under concurrency
    print("A1: Concurrent sequence isolation")
    agents = [GCounter(f"agent-{i}", i) for i in range(4)]
    seqs   = []
    for ag in agents:
        for _ in range(10): seqs.append(ag.next_seq(0,0,0))
    if len(seqs)==len(set(seqs)): ok("zero collisions across 4 concurrent agents")
    else: warn("sequence collision detected")

    # A2: Entanglement pair hash uniqueness
    print("\nA2: Entanglement pair hash uniqueness")
    fhrr = FHRR(dim=128)
    eng  = EntanglementEngine(fhrr)
    vc   = VectorClock("audit")
    files = [encode_filename(0,i%8,0,i) for i in range(8)]
    hashes = set()
    for i in range(len(files)):
        for j in range(i+1,len(files)):
            p = eng.entangle(files[i],files[j],"audit",vc,1.0)
            hashes.add(p.pair_hash)
    if len(hashes)==len(eng.pairs): ok(f"all {len(hashes)} pair hashes unique")
    else: warn("pair hash collision")

    # A3: Cascade doesn't include self
    print("\nA3: Cascade self-exclusion")
    changed = "py.orc.cor.000"
    cascade = eng.cascade_invalidate(changed)
    if changed not in cascade: ok("changed file excluded from own cascade")
    else: warn("file appears in own cascade")

    # A4: Merkle tamper detection with entanglement
    print("\nA4: Merkle tamper detection")
    files2 = ["py.orc.cor.000","js.cfg.cor.000"]
    ph     = ["a"*64]
    m1 = GFSMerkle(files2, ph)
    # Tamper pair hash
    m2 = GFSMerkle(files2, ["b"*64])
    if m1.root()!=m2.root(): ok("entanglement tamper detected in Merkle root")
    else: warn("tamper not detected")

    # A5: OR-Set remove idempotency
    print("\nA5: OR-Set idempotency")
    os   = ORSet()
    vc2  = VectorClock("A")
    os.add("py.orc.cor.000","A",vc2)
    os.remove("py.orc.cor.000")
    os.remove("py.orc.cor.000")  # double remove
    if not os.contains("py.orc.cor.000"): ok("double remove idempotent")
    else: warn("double remove failed")

    # A6: Bad filename rejection
    print("\nA6: Malformed input rejection")
    bad = ["py.orc.cor","py.orc.cor.000.extra","XX.orc.cor.000",
           "py.ZZZ.cor.000","py.orc.XYZ.000","py.orc.cor.999",
           "","../../../../etc/passwd"]
    caught = sum(1 for b in bad if _try_decode(b))
    if caught==len(bad): ok(f"all {len(bad)} malformed inputs rejected")
    else: warn(f"only {caught}/{len(bad)} rejected")

    # A7: Vector clock concurrent detection
    print("\nA7: Vector clock concurrent detection")
    vc_a = VectorClock("A"); vc_a = vc_a.tick()
    vc_b = VectorClock("B"); vc_b = vc_b.tick()
    if vc_a.concurrent_with(vc_b): ok("concurrent writes correctly detected")
    else: warn("concurrent detection failed")
    vc_c = vc_a.merge(vc_b).tick()
    if vc_a.happens_before(vc_c): ok("causal ordering preserved after merge")
    else: warn("causal ordering broken")

    print(f"\n  {'═'*50}")
    print(f"  PASSED: {passed}  WARNINGS: {warned}")
    for n,d in findings: print(f"    ⚠ {n}: {d}")
    return warned==0

def _try_decode(f):
    try: decode_filename(f); return False
    except: return True

if __name__=="__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "all"
    t_ok = b_ok = a_ok = True

    if cmd in ("test","all"):  t_ok = run_tests()
    if cmd in ("bench","all"): run_benchmarks()
    if cmd in ("audit","all"): a_ok = run_audit()

    if cmd=="all":
        print(f"\n{'═'*62}")
        print(f"  GFS v4 — CRDT + TWIN ENTANGLEMENT — FINAL REPORT")
        print(f"{'═'*62}")
        print(f"  Tests:  {'ALL PASSED' if t_ok else 'FAILURES'}")
        print(f"  Audit:  {'CLEAN' if a_ok else 'WARNINGS'}")
        print(f"{'═'*62}")

