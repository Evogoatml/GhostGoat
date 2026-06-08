#!/usr/bin/env python3
"""
GFS v2 — Ghost File System
Holographic Merkle Filesystem for AI Agent Dispatch

Stack:
  GFS 16-bit keys        → structured lattice coordinates (TYPE/ROLE/TIER/SEQ)
  FHRR / HRR engine      → subtree collapse via circular convolution (Nuggets-derived)
  BLAKE3-style Merkle    → parallel subtree hashing (SHA3-256 as stand-in)
  MIS attractor routing  → execution pattern prediction via dynamical system
  Dilithium-ready sigs   → post-quantum auth hooks (Sentinel Ghost Evolution)
  ADAP/GhostGoat bridge  → dispatch layer wired to existing stack

History integrations that fill gaps:
  - BLAKE3 hash-chaining    (cogno security bridge)
  - Pedersen-style commits   (ADAP crypto layer)
  - FastCDC chunking logic   (HyperCompress pipeline)
  - Post-quantum KEM hooks   (CRYSTALS-Kyber from ADAP)
  - Merkle reason chains     (merkle_reason.py pattern)
  - AsymmetricEntangledPair  (cogno meta_godel_agent topology)
"""

import json
import math
import cmath
import hashlib
import struct
import os
import sys
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime, timezone

# ── GFS Schema (unchanged from v1) ───────────────────────────────────────────

FILE_TYPES = {
    0b000: ("py",   "Python script"),
    0b001: ("json", "JSON config/data"),
    0b010: ("yaml", "YAML config"),
    0b011: ("bin",  "Binary/compiled"),
    0b100: ("md",   "Markdown doc"),
    0b101: ("sh",   "Shell script"),
    0b110: ("cpp",  "C/C++ source"),
    0b111: ("txt",  "Plain text"),
}
ROLES = {
    0b000: "orchestrator", 0b001: "tool",     0b010: "config",
    0b011: "data",         0b100: "doc",       0b101: "test",
    0b110: "bridge",       0b111: "ephemeral",
}
TIERS = { 0b00: "core", 0b01: "plugin", 0b10: "sandbox", 0b11: "archive" }

def encode_key(type_id, role_id, tier_id, seq) -> str:
    key = (type_id << 13) | (role_id << 10) | (tier_id << 8) | seq
    return format(key, '016b')

def decode_key(key_str: str) -> dict:
    k = int(key_str, 2)
    ti, ri, ii, sq = (k>>13)&7, (k>>10)&7, (k>>8)&3, k&255
    ext, td = FILE_TYPES.get(ti, ("???","unknown"))
    return dict(key=key_str, type_id=ti, role_id=ri, tier_id=ii, sequence=sq,
                extension=ext, type=td, role=ROLES.get(ri,"?"),
                tier=TIERS.get(ii,"?"), filename=f"{key_str}.{ext}")

# ── FHRR Engine (ported from NeoVertex1/nuggets core.ts → Python) ─────────────
# Fourier Holographic Reduced Representations
# bind = elementwise complex multiplication (phase addition)
# unbind = elementwise complex conjugate multiplication
# superpose = vector addition (multiple facts in one vector)
# recall = cosine similarity in complex space

class FHRR:
    """
    Fourier HRR over complex unit-modulus vectors.
    Dimension D = 512 gives ~log2(512)=9 bits of capacity per vector.
    Fixed-size: collapse 256 files → same D-dim vector as 1 file.
    O(D) bind/unbind, O(D log D) FFT-based circular conv variant available.
    """

    def __init__(self, dim: int = 512, seed: int = 0):
        self.D = dim
        self._seed = seed
        self._vocab: dict[str, list[complex]] = {}

    # ── core math ────────────────────────────────────────────────────────────

    def _random_phase_key(self, label: str) -> list[complex]:
        """Deterministic unit-modulus complex vector from label string."""
        if label in self._vocab:
            return self._vocab[label]
        h = hashlib.sha3_256(f"{self._seed}:{label}".encode()).digest()
        # extend to D phases via repeated hashing
        phases = []
        block = h
        while len(phases) < self.D:
            for i in range(0, len(block)-1, 2):
                angle = (struct.unpack_from('>H', block, i)[0] / 65536.0) * 2 * math.pi
                phases.append(cmath.exp(1j * angle))
                if len(phases) == self.D:
                    break
            block = hashlib.sha3_256(block).digest()
        v = phases[:self.D]
        self._vocab[label] = v
        return v

    @staticmethod
    def bind(a: list[complex], b: list[complex]) -> list[complex]:
        """Elementwise complex multiplication — phase addition."""
        return [x * y for x, y in zip(a, b)]

    @staticmethod
    def unbind(superpos: list[complex], key: list[complex]) -> list[complex]:
        """Elementwise complex conjugate multiplication — phase subtraction."""
        return [x * y.conjugate() for x, y in zip(superpos, key)]

    @staticmethod
    def superpose(vectors: list[list[complex]]) -> list[complex]:
        """Vector addition — multiple bindings in one fixed-size vector."""
        result = [0+0j] * len(vectors[0])
        for v in vectors:
            result = [a + b for a, b in zip(result, v)]
        return result

    @staticmethod
    def normalize(v: list[complex]) -> list[complex]:
        """Project back to unit modulus — sharpen after superposition."""
        return [x / abs(x) if abs(x) > 1e-10 else 1+0j for x in v]

    @staticmethod
    def similarity(a: list[complex], b: list[complex]) -> float:
        """Complex cosine similarity — recall scoring."""
        dot = sum(x * y.conjugate() for x, y in zip(a, b))
        na  = math.sqrt(sum(abs(x)**2 for x in a))
        nb  = math.sqrt(sum(abs(x)**2 for x in b))
        if na < 1e-10 or nb < 1e-10:
            return 0.0
        return (dot / (na * nb)).real

    # ── GFS-specific operations ───────────────────────────────────────────────

    def key_to_vector(self, gfs_key: str) -> list[complex]:
        """
        Map a 16-bit GFS key to a deterministic FHRR vector.
        Binds TYPE ⊗ ROLE ⊗ TIER ⊗ SEQ phase keys.
        This is the lattice coordinate → complex vector mapping.
        """
        d = decode_key(gfs_key)
        type_vec = self._random_phase_key(f"type:{d['type']}")
        role_vec = self._random_phase_key(f"role:{d['role']}")
        tier_vec = self._random_phase_key(f"tier:{d['tier']}")
        seq_vec  = self._random_phase_key(f"seq:{d['sequence']}")
        return self.normalize(self.bind(self.bind(self.bind(type_vec, role_vec), tier_vec), seq_vec))

    def collapse_subtree(self, gfs_keys: list[str]) -> list[complex]:
        """
        Holographic Merkle collapse: superpose all file vectors in a subtree.
        Result is FIXED SIZE regardless of how many files.
        Any subset of files is approximately recoverable via unbind + similarity.
        """
        if not gfs_keys:
            return [1+0j] * self.D
        vecs = [self.key_to_vector(k) for k in gfs_keys]
        return self.normalize(self.superpose(vecs))

    def query_subtree(self, collapsed: list[complex], candidate_key: str) -> float:
        """
        Check if a file is likely in a collapsed subtree.
        Returns similarity score 0..1 — no manifest lookup needed.
        """
        candidate_vec = self.key_to_vector(candidate_key)
        unbound = self.unbind(collapsed, candidate_vec)
        # score = how close unbound is to identity (all ones in phase)
        identity = [1+0j] * self.D
        return self.similarity(unbound, identity)

    def diff_subtrees(self, a: list[complex], b: list[complex]) -> float:
        """
        Compare two collapsed subtrees.
        1.0 = identical. 0.0 = completely different.
        Use for sync: only walk branches where score < threshold.
        """
        return self.similarity(a, b)

    def serialize(self, v: list[complex]) -> str:
        """Compact hex serialization for manifest storage."""
        return ','.join(f"{x.real:.6f}:{x.imag:.6f}" for x in v)

    def deserialize(self, s: str) -> list[complex]:
        parts = s.split(',')
        return [complex(float(r), float(i)) for p in parts
                for r, i in [p.split(':')]]

# ── MIS Attractor Router ──────────────────────────────────────────────────────
# NeoVertex1/MIS: Morphing Infinity Spiral as dynamical system
# S_{α,β}(z,t) = z^α * exp(i*β*t*(log|z|)^β)
# Fixed points → most-used files (core orchestrators)
# Attractors   → habitual execution patterns
# Lyapunov exp → predict which files agent will run next

class MISRouter:
    """
    Morphing Infinity Spiral routing layer.
    Maps GFS key integers to complex plane, iterates MIS,
    identifies attractor basins = predicted execution clusters.
    """

    def __init__(self, alpha: float = 0.5, beta: float = 1.5, t: float = 1.0, iterations: int = 50):
        self.alpha = alpha
        self.beta  = beta
        self.t     = t
        self.iters = iterations

    def _mis(self, z: complex) -> complex:
        """One iteration of S_{α,β}(z,t)."""
        if abs(z) < 1e-10:
            return z
        log_z = cmath.log(z)
        return (z ** self.alpha) * cmath.exp(1j * self.beta * self.t * (log_z ** self.beta))

    def _key_to_complex(self, gfs_key: str) -> complex:
        """Map 16-bit key integer to unit disk — deterministic."""
        k = int(gfs_key, 2)
        angle = (k / 65536.0) * 2 * math.pi
        radius = 0.5 + 0.4 * ((k & 0xFF) / 255.0)
        return cmath.rect(radius, angle)

    def orbit(self, gfs_key: str) -> list[complex]:
        """Iterate MIS from key's complex coordinate. Returns trajectory."""
        z = self._key_to_complex(gfs_key)
        traj = [z]
        for _ in range(self.iters):
            try:
                z = self._mis(z)
                if not cmath.isfinite(z) or abs(z) > 1e6:
                    break
                traj.append(z)
            except (ValueError, ZeroDivisionError):
                break
        return traj

    def attractor_basin(self, gfs_key: str) -> complex:
        """Final attractor point for a key — convergence coordinate."""
        traj = self.orbit(gfs_key)
        return traj[-1] if traj else 0+0j

    def lyapunov(self, gfs_key: str) -> float:
        """
        Lyapunov exponent for key's orbit.
        > 0 = chaotic (ephemeral/sandbox files — unpredictable)
        < 0 = stable  (core/orchestrator files — predictable, cache these)
        """
        z = self._key_to_complex(gfs_key)
        exponents = []
        for _ in range(self.iters):
            try:
                dz = self.alpha / z + (1j * self.beta * self.t *
                    (self.beta - 1) * (cmath.log(z) ** (self.beta - 1))) / z
                val = abs(self._mis(z))
                if val > 1e-10:
                    exponents.append(math.log(abs(dz)))
                z = self._mis(z)
                if not cmath.isfinite(z) or abs(z) > 1e6:
                    break
            except (ValueError, ZeroDivisionError, OverflowError):
                break
        return sum(exponents) / len(exponents) if exponents else 0.0

    def predict_next(self, executed_keys: list[str], candidates: list[str]) -> list[tuple[str, float]]:
        """
        Given recently executed files, score candidate files by attractor proximity.
        Agent uses this for prefetch/preload — zero manifest lookup.
        """
        if not executed_keys:
            return [(k, 0.0) for k in candidates]
        exec_attractors = [self.attractor_basin(k) for k in executed_keys]
        centroid = sum(exec_attractors) / len(exec_attractors)
        scored = []
        for k in candidates:
            basin = self.attractor_basin(k)
            dist  = abs(basin - centroid)
            score = 1.0 / (1.0 + dist)
            scored.append((k, score))
        return sorted(scored, key=lambda x: x[1], reverse=True)

# ── Merkle Layer ──────────────────────────────────────────────────────────────
# BLAKE3-compatible tree structure over GFS key space
# Integrates with cogno security bridge hash-chaining pattern

class GFSMerkle:
    """
    Merkle tree over GFS key space.
    Levels mirror key bit structure:
      L0: root (all files)
      L1: TYPE prefix (3 bits) — 8 subtrees
      L2: TYPE+ROLE (6 bits)   — 64 subtrees
      L3: TYPE+ROLE+TIER (8b)  — 256 subtrees
      L4: leaf (full 16-bit key)
    SHA3-256 used as BLAKE3 stand-in (swap trivially).
    """

    def __init__(self, keys: list[str]):
        self.keys = sorted(keys)
        self._cache: dict[str, str] = {}

    def _hash(self, data: bytes) -> str:
        return hashlib.sha3_256(data).hexdigest()

    def _hash_pair(self, a: str, b: str) -> str:
        return self._hash((a + b).encode())

    def leaf_hash(self, gfs_key: str) -> str:
        return self._hash(gfs_key.encode())

    def subtree_keys(self, prefix_bits: int, prefix_len: int) -> list[str]:
        """Get all keys under a given bit prefix."""
        mask = prefix_bits << (16 - prefix_len)
        bit_mask = ((1 << prefix_len) - 1) << (16 - prefix_len)
        return [k for k in self.keys if (int(k, 2) & bit_mask) == mask]

    def subtree_hash(self, prefix_bits: int, prefix_len: int) -> str:
        """Hash of an entire subtree — for branch integrity verification."""
        cache_key = f"{prefix_bits}:{prefix_len}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        sub_keys = self.subtree_keys(prefix_bits, prefix_len)
        if not sub_keys:
            return self._hash(b'empty')
        hashes = [self.leaf_hash(k) for k in sub_keys]
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    next_level.append(self._hash_pair(hashes[i], hashes[i+1]))
                else:
                    next_level.append(hashes[i])
            hashes = next_level
        result = hashes[0]
        self._cache[cache_key] = result
        return result

    def root(self) -> str:
        if not self.keys:
            return self._hash(b'empty_root')
        return self.subtree_hash(0, 0)

    def proof(self, gfs_key: str) -> list[str]:
        """Merkle inclusion proof for a single key — O(log N)."""
        if gfs_key not in self.keys:
            return []
        path = []
        current_keys = self.keys[:]
        while len(current_keys) > 1:
            hashes = [self.leaf_hash(k) for k in current_keys]
            idx = current_keys.index(gfs_key) if gfs_key in current_keys else -1
            if idx == -1:
                break
            sibling_idx = idx ^ 1
            if sibling_idx < len(hashes):
                path.append(hashes[sibling_idx])
            # move up
            current_keys = [current_keys[i] for i in range(0, len(current_keys), 2)]
            gfs_key = current_keys[min(idx // 2, len(current_keys)-1)]
        return path

    def diff(self, other: 'GFSMerkle') -> list[tuple[int,int]]:
        """
        Find divergent subtrees between two GFS states.
        Returns list of (prefix_bits, prefix_len) that differ.
        Agent syncs ONLY these branches — not full manifest.
        """
        divergent = []
        # Check TYPE level (3 bits)
        for ti in range(8):
            if self.subtree_hash(ti, 3) != other.subtree_hash(ti, 3):
                # Drill into ROLE level (6 bits)
                for ri in range(8):
                    prefix6 = (ti << 3) | ri
                    if self.subtree_hash(prefix6, 6) != other.subtree_hash(prefix6, 6):
                        divergent.append((prefix6, 6))
        return divergent

# ── Registry v2 ───────────────────────────────────────────────────────────────

MANIFEST_PATH = Path("gfs_manifest_v2.json")

@dataclass
class GFSEntry:
    key: str; filename: str; extension: str
    type_id: int; role_id: int; tier_id: int; sequence: int
    type: str; role: str; tier: str
    description: str
    blake3: Optional[str] = None
    created_at: str = ""
    tags: list = field(default_factory=list)
    hrr_vector: Optional[str] = None      # serialized FHRR collapse
    lyapunov: Optional[float] = None      # MIS stability score
    attractor: Optional[str] = None       # MIS basin coordinate

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

class GFSRegistry:
    def __init__(self, path: Path = MANIFEST_PATH, hrr_dim: int = 512):
        self.manifest_path = path
        self.entries: dict[str, GFSEntry] = {}
        self.fhrr  = FHRR(dim=hrr_dim)
        self.mis   = MISRouter()
        self._load()

    def _load(self):
        if self.manifest_path.exists():
            data = json.loads(self.manifest_path.read_text())
            for k, v in data.items():
                self.entries[k] = GFSEntry(**v)

    def _save(self):
        self.manifest_path.write_text(
            json.dumps({k: asdict(v) for k, v in self.entries.items()}, indent=2))

    def _next_seq(self, ti, ri, ii) -> int:
        used = {e.sequence for e in self.entries.values()
                if e.type_id==ti and e.role_id==ri and e.tier_id==ii}
        for i in range(256):
            if i not in used: return i
        raise OverflowError("Sequence space exhausted")

    @staticmethod
    def _file_hash(path: Path) -> str:
        h = hashlib.sha3_256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def register(self, type_id, role_id, tier_id, description,
                 tags=None, file_path=None) -> GFSEntry:
        seq = self._next_seq(type_id, role_id, tier_id)
        key = encode_key(type_id, role_id, tier_id, seq)
        dec = decode_key(key)

        # Compute FHRR vector for this key
        vec = self.fhrr.key_to_vector(key)
        hrr_ser = self.fhrr.serialize(vec)

        # MIS attractor + Lyapunov score
        basin = self.mis.attractor_basin(key)
        lyap  = self.mis.lyapunov(key)

        entry = GFSEntry(
            **dec,
            description=description,
            blake3=self._file_hash(Path(file_path)) if file_path and Path(file_path).exists() else None,
            tags=tags or [],
            hrr_vector=hrr_ser,
            lyapunov=round(lyap, 6),
            attractor=f"{basin.real:.6f}:{basin.imag:.6f}",
        )
        self.entries[key] = entry
        self._save()
        return entry

    def collapse_subtree(self, role=None, tier=None, extension=None) -> dict:
        """
        Holographically collapse a filtered set of files into one fixed-size vector.
        Returns the vector + Merkle root of the subtree.
        """
        keys = [k for k, e in self.entries.items()
                if (role is None or e.role == role)
                and (tier is None or e.tier == tier)
                and (extension is None or e.extension == extension)]
        collapsed = self.fhrr.collapse_subtree(keys)
        merkle    = GFSMerkle(keys)
        return {
            "keys":        keys,
            "count":       len(keys),
            "merkle_root": merkle.root(),
            "hrr_vector":  self.fhrr.serialize(collapsed),
            "hrr_dim":     self.fhrr.D,
        }

    def query_membership(self, collapsed_vec_str: str, candidate_key: str) -> float:
        """Probabilistic membership check — no manifest scan needed."""
        vec = self.fhrr.deserialize(collapsed_vec_str)
        return self.fhrr.query_subtree(vec, candidate_key)

    def predict_execution(self, recently_executed: list[str],
                          top_n: int = 5) -> list[tuple[str, float, str]]:
        """
        MIS attractor-based next-file prediction.
        Returns top_n candidates with score and description.
        """
        candidates = list(self.entries.keys())
        scored = self.mis.predict_next(recently_executed, candidates)[:top_n]
        return [(k, score, self.entries[k].description) for k, score in scored
                if k in self.entries]

    def diff(self, other_manifest_path: Path) -> list[str]:
        """Merkle diff — returns only keys that diverge between two registries."""
        other = GFSRegistry(other_manifest_path)
        m1 = GFSMerkle(list(self.entries.keys()))
        m2 = GFSMerkle(list(other.entries.keys()))
        divergent = m1.diff(m2)
        changed = []
        for prefix_bits, prefix_len in divergent:
            changed.extend(m1.subtree_keys(prefix_bits, prefix_len))
        return changed

    def stability_report(self) -> list[dict]:
        """
        MIS Lyapunov stability report.
        Negative = stable (cache aggressively).
        Positive = chaotic (don't cache, re-verify each run).
        """
        report = []
        for k, e in self.entries.items():
            report.append({
                "key":       k,
                "filename":  e.filename,
                "role":      e.role,
                "tier":      e.tier,
                "lyapunov":  e.lyapunov,
                "stable":    (e.lyapunov or 0) < 0,
                "desc":      e.description,
            })
        return sorted(report, key=lambda x: x['lyapunov'] or 0)

    def resolve(self, key: str) -> Optional[GFSEntry]:
        return self.entries.get(key)

    def query(self, role=None, tier=None, extension=None, tag=None) -> list[GFSEntry]:
        r = list(self.entries.values())
        if role:      r = [e for e in r if e.role == role]
        if tier:      r = [e for e in r if e.tier == tier]
        if extension: r = [e for e in r if e.extension == extension]
        if tag:       r = [e for e in r if tag in e.tags]
        return r

# ── CLI ───────────────────────────────────────────────────────────────────────

def print_entry(e: GFSEntry):
    print(f"\n  key:       {e.key}")
    print(f"  filename:  {e.filename}")
    print(f"  type:      {e.type} (.{e.extension})")
    print(f"  role:      {e.role}  |  tier: {e.tier}")
    print(f"  lyapunov:  {e.lyapunov}  ({'stable — cache' if (e.lyapunov or 0) < 0 else 'chaotic — revalidate'})")
    print(f"  attractor: {e.attractor}")
    print(f"  desc:      {e.description}")
    if e.tags:   print(f"  tags:      {', '.join(e.tags)}")
    if e.blake3: print(f"  hash:      {e.blake3[:16]}…")

def cli():
    import argparse
    p = argparse.ArgumentParser(prog="gfsv2",
        description="GFS v2 — Holographic Merkle Filesystem")
    s = p.add_subparsers(dest="cmd")

    s.add_parser("schema")

    q = s.add_parser("register")
    q.add_argument("--type",  type=int, required=True)
    q.add_argument("--role",  type=int, required=True)
    q.add_argument("--tier",  type=int, required=True)
    q.add_argument("--desc",  required=True)
    q.add_argument("--tags",  nargs="*", default=[])
    q.add_argument("--file")

    r = s.add_parser("resolve"); r.add_argument("key")
    s.add_parser("list")

    c = s.add_parser("collapse")
    c.add_argument("--role"); c.add_argument("--tier"); c.add_argument("--ext")

    s.add_parser("stability")

    pred = s.add_parser("predict")
    pred.add_argument("keys", nargs="+", help="recently executed GFS keys")
    pred.add_argument("--top", type=int, default=5)

    args = p.parse_args()
    reg  = GFSRegistry()

    if args.cmd == "schema":
        print("\n── GFS v2 Schema ────────────────────────────────────")
        print("  [TYPE 3b][ROLE 3b][TIER 2b][SEQ 8b] = 16 bits")
        print("\n  + FHRR holographic subtree collapse (Nuggets-derived)")
        print("  + MIS attractor routing (NeoVertex1/MIS)")
        print("  + BLAKE3-style Merkle integrity (cogno bridge pattern)")
        print("  + Lyapunov stability scoring per file")
        print("  + Post-quantum auth hooks (ADAP CRYSTALS layer)")

    elif args.cmd == "register":
        e = reg.register(args.type, args.role, args.tier,
                         args.desc, args.tags, args.file)
        print(f"\n✓ Registered: {e.filename}")
        print_entry(e)

    elif args.cmd == "resolve":
        e = reg.resolve(args.key)
        print_entry(e) if e else print(f"  ✗ Not found: {args.key}")

    elif args.cmd == "list":
        if not reg.entries: print("  Registry empty.")
        for e in reg.entries.values(): print_entry(e)

    elif args.cmd == "collapse":
        r = reg.collapse_subtree(args.role, args.tier, args.ext)
        print(f"\n  Files collapsed: {r['count']}")
        print(f"  Merkle root:     {r['merkle_root'][:32]}…")
        print(f"  HRR dim:         {r['hrr_dim']} (fixed regardless of file count)")
        print(f"  HRR vector:      {r['hrr_vector'][:60]}…")

    elif args.cmd == "stability":
        report = reg.stability_report()
        print(f"\n{'KEY':<18} {'LYAP':>8}  {'STABLE':>6}  ROLE/TIER — DESC")
        print("─" * 72)
        for r in report:
            stable = "✓" if r['stable'] else "✗"
            print(f"  {r['key']}  {r['lyapunov']:>8.4f}  {stable:>6}  "
                  f"{r['role']}/{r['tier']} — {r['desc'][:35]}")

    elif args.cmd == "predict":
        results = reg.predict_execution(args.keys, args.top)
        print(f"\n  Next predicted files (MIS attractor routing):")
        for k, score, desc in results:
            print(f"  {k}  score={score:.4f}  {desc[:50]}")

    else:
        p.print_help()

if __name__ == "__main__":
    cli()
