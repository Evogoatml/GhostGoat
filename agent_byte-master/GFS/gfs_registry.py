#!/usr/bin/env python3
"""
GFS — Ghost File System
16-bit structured binary key encoding for AI-addressable file retrieval.

Key structure (16 bits):
  [TYPE 3bit][ROLE 3bit][TIER 2bit][SEQUENCE 8bit]

Filename format: {16bit_key}.{extension}
Example: 0100100000000001.py
"""

import json
import os
import sys
import struct
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime, timezone

# ── Schema ────────────────────────────────────────────────────────────────────

FILE_TYPES = {
    0b000: ("py",   "Python script"),
    0b001: ("json", "JSON config/data"),
    0b010: ("yaml", "YAML config"),
    0b011: ("bin",  "Binary/compiled artifact"),
    0b100: ("md",   "Markdown document"),
    0b101: ("sh",   "Shell script"),
    0b110: ("cpp",  "C/C++ source"),
    0b111: ("txt",  "Plain text / misc"),
}

ROLES = {
    0b000: "orchestrator",   # top-level coordinator / entry point
    0b001: "tool",           # callable tool / plugin
    0b010: "config",         # configuration / settings
    0b011: "data",           # data payload / dataset
    0b100: "doc",            # documentation / reference
    0b101: "test",           # test / benchmark
    0b110: "bridge",         # inter-system bridge / adapter
    0b111: "ephemeral",      # temp / scratch / one-shot
}

TIERS = {
    0b00: "core",       # system-critical, always loaded
    0b01: "plugin",     # loadable extension
    0b10: "sandbox",    # isolated / experimental
    0b11: "archive",    # frozen / versioned snapshot
}

MANIFEST_PATH = Path("gfs_manifest.json")

# ── Key Encoding / Decoding ───────────────────────────────────────────────────

def encode_key(type_id: int, role_id: int, tier_id: int, seq: int) -> str:
    """Encode a 16-bit GFS key as a zero-padded binary string."""
    assert 0 <= type_id <= 7,  f"type_id out of range: {type_id}"
    assert 0 <= role_id <= 7,  f"role_id out of range: {role_id}"
    assert 0 <= tier_id <= 3,  f"tier_id out of range: {tier_id}"
    assert 0 <= seq    <= 255, f"sequence out of range: {seq}"
    key = (type_id << 13) | (role_id << 10) | (tier_id << 8) | seq
    return format(key, '016b')

def decode_key(key_str: str) -> dict:
    """Decode a 16-bit binary string into its GFS components."""
    if len(key_str) != 16 or not all(c in '01' for c in key_str):
        raise ValueError(f"Invalid GFS key: '{key_str}' — must be 16 binary digits")
    key = int(key_str, 2)
    type_id = (key >> 13) & 0b111
    role_id = (key >> 10) & 0b111
    tier_id = (key >> 8)  & 0b11
    seq     =  key        & 0b11111111
    ext, type_desc = FILE_TYPES.get(type_id, ("???", "unknown"))
    return {
        "key":       key_str,
        "type_id":   type_id,
        "role_id":   role_id,
        "tier_id":   tier_id,
        "sequence":  seq,
        "extension": ext,
        "type":      type_desc,
        "role":      ROLES.get(role_id, "unknown"),
        "tier":      TIERS.get(tier_id, "unknown"),
        "filename":  f"{key_str}.{ext}",
    }

# ── Registry ──────────────────────────────────────────────────────────────────

@dataclass
class GFSEntry:
    key:         str
    filename:    str
    extension:   str
    type_id:     int
    role_id:     int
    tier_id:     int
    sequence:    int
    type:        str
    role:        str
    tier:        str
    description: str
    blake3:      Optional[str] = None
    created_at:  str = ""
    tags:        list = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

class GFSRegistry:
    def __init__(self, manifest_path: Path = MANIFEST_PATH):
        self.manifest_path = manifest_path
        self.entries: dict[str, GFSEntry] = {}
        self._load()

    def _load(self):
        if self.manifest_path.exists():
            data = json.loads(self.manifest_path.read_text())
            for k, v in data.items():
                self.entries[k] = GFSEntry(**v)

    def _save(self):
        out = {k: asdict(v) for k, v in self.entries.items()}
        self.manifest_path.write_text(json.dumps(out, indent=2))

    def _next_seq(self, type_id: int, role_id: int, tier_id: int) -> int:
        used = set()
        for e in self.entries.values():
            if e.type_id == type_id and e.role_id == role_id and e.tier_id == tier_id:
                used.add(e.sequence)
        for i in range(256):
            if i not in used:
                return i
        raise OverflowError("Sequence space exhausted for this type/role/tier combination")

    def register(
        self,
        type_id: int,
        role_id: int,
        tier_id: int,
        description: str,
        tags: list[str] = None,
        file_path: Optional[Path] = None,
    ) -> GFSEntry:
        seq = self._next_seq(type_id, role_id, tier_id)
        key = encode_key(type_id, role_id, tier_id, seq)
        decoded = decode_key(key)

        blake3_hash = None
        if file_path and Path(file_path).exists():
            blake3_hash = self._hash_file(Path(file_path))

        entry = GFSEntry(
            **decoded,
            description=description,
            blake3=blake3_hash,
            tags=tags or [],
        )
        self.entries[key] = entry
        self._save()
        return entry

    def resolve(self, key: str) -> Optional[GFSEntry]:
        return self.entries.get(key)

    def query(
        self,
        role: Optional[str] = None,
        tier: Optional[str] = None,
        extension: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[GFSEntry]:
        results = list(self.entries.values())
        if role:
            results = [e for e in results if e.role == role]
        if tier:
            results = [e for e in results if e.tier == tier]
        if extension:
            results = [e for e in results if e.extension == extension]
        if tag:
            results = [e for e in results if tag in e.tags]
        return results

    def remove(self, key: str) -> bool:
        if key in self.entries:
            del self.entries[key]
            self._save()
            return True
        return False

    @staticmethod
    def _hash_file(path: Path) -> str:
        """SHA3-256 as blake3 stand-in (no external dep required)."""
        h = hashlib.sha3_256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

# ── CLI ───────────────────────────────────────────────────────────────────────

def print_schema():
    print("\n── GFS 16-bit Key Schema ─────────────────────────────")
    print("  [TYPE 3b][ROLE 3b][TIER 2b][SEQUENCE 8b] = 16 bits\n")
    print("FILE TYPES (bits 15-13):")
    for k, (ext, desc) in FILE_TYPES.items():
        print(f"  {format(k,'03b')} → .{ext:<6} {desc}")
    print("\nROLES (bits 12-10):")
    for k, v in ROLES.items():
        print(f"  {format(k,'03b')} → {v}")
    print("\nTIERS (bits 9-8):")
    for k, v in TIERS.items():
        print(f"  {format(k,'02b')} → {v}")
    print("\nSEQUENCE (bits 7-0): 0–255 per type/role/tier combination")
    print(f"\nTotal addressable files: {8*8*4*256:,} ({8*8*4*256} slots)\n")

def print_entry(entry: GFSEntry):
    print(f"\n  key:      {entry.key}")
    print(f"  filename: {entry.filename}")
    print(f"  type:     {entry.type} (.{entry.extension})")
    print(f"  role:     {entry.role}")
    print(f"  tier:     {entry.tier}")
    print(f"  desc:     {entry.description}")
    if entry.tags:
        print(f"  tags:     {', '.join(entry.tags)}")
    if entry.blake3:
        print(f"  hash:     {entry.blake3[:16]}…")
    print(f"  created:  {entry.created_at}")

def cli():
    import argparse
    parser = argparse.ArgumentParser(
        prog="gfs",
        description="Ghost File System — AI-addressable binary key registry"
    )
    sub = parser.add_subparsers(dest="cmd")

    # schema
    sub.add_parser("schema", help="Print full encoding schema")

    # decode
    p = sub.add_parser("decode", help="Decode a 16-bit GFS key")
    p.add_argument("key", help="16-bit binary string e.g. 0000000000000001")

    # register
    p = sub.add_parser("register", help="Register a new file into the GFS manifest")
    p.add_argument("--type",  type=int, required=True, help="File type ID (0-7)")
    p.add_argument("--role",  type=int, required=True, help="Role ID (0-7)")
    p.add_argument("--tier",  type=int, required=True, help="Tier ID (0-3)")
    p.add_argument("--desc",  required=True, help="Description")
    p.add_argument("--tags",  nargs="*", default=[])
    p.add_argument("--file",  help="Path to file (for hash)")

    # resolve
    p = sub.add_parser("resolve", help="Resolve a key to its registry entry")
    p.add_argument("key")

    # query
    p = sub.add_parser("query", help="Query registry by role/tier/extension/tag")
    p.add_argument("--role",  help="Filter by role name")
    p.add_argument("--tier",  help="Filter by tier name")
    p.add_argument("--ext",   help="Filter by extension")
    p.add_argument("--tag",   help="Filter by tag")

    # list
    sub.add_parser("list", help="List all registered files")

    # remove
    p = sub.add_parser("remove", help="Remove a key from the registry")
    p.add_argument("key")

    args = parser.parse_args()
    reg  = GFSRegistry()

    if args.cmd == "schema":
        print_schema()

    elif args.cmd == "decode":
        d = decode_key(args.key)
        for k, v in d.items():
            print(f"  {k:<12} {v}")

    elif args.cmd == "register":
        entry = reg.register(
            type_id=args.type,
            role_id=args.role,
            tier_id=args.tier,
            description=args.desc,
            tags=args.tags,
            file_path=args.file,
        )
        print(f"\n✓ Registered: {entry.filename}")
        print_entry(entry)

    elif args.cmd == "resolve":
        entry = reg.resolve(args.key)
        if entry:
            print_entry(entry)
        else:
            print(f"  ✗ Key not found: {args.key}")
            sys.exit(1)

    elif args.cmd == "query":
        results = reg.query(
            role=args.role, tier=args.tier,
            extension=args.ext, tag=args.tag
        )
        print(f"\n{len(results)} result(s):")
        for e in results:
            print_entry(e)

    elif args.cmd == "list":
        if not reg.entries:
            print("  Registry is empty.")
        for e in reg.entries.values():
            print_entry(e)

    elif args.cmd == "remove":
        if reg.remove(args.key):
            print(f"  ✓ Removed: {args.key}")
        else:
            print(f"  ✗ Key not found: {args.key}")

    else:
        parser.print_help()

if __name__ == "__main__":
    cli()

