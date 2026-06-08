# GFS — Ghost File System Specification
**Version 1.0 | Sentinel Ghost Evolution**

## Problem

Human-readable filenames introduce semantic ambiguity into AI retrieval pipelines.
An AI agent resolving `compress_utils.py` vs `compression_helper.py` vs `crypto_compress.py`
must parse language, infer intent, and risk misresolution. At scale this is a reliability failure.

## Solution

Replace filenames with **structured 16-bit binary keys**. The key encodes identity.
The extension encodes language. The manifest encodes metadata. Nothing else matters for dispatch.

---

## Key Structure

```
Bit position:  15 14 13 | 12 11 10 | 9 8 | 7 6 5 4 3 2 1 0
Field:         [ TYPE  ] | [ ROLE ] |[TIER]|   [ SEQUENCE  ]
Bits:              3     |     3    |  2   |        8
```

**Total addressable files: 65,536** (8 types × 8 roles × 4 tiers × 256 sequences)

---

## Field Definitions

### TYPE (bits 15–13) — Language / Format

| Bits | Extension | Description              |
|------|-----------|--------------------------|
| 000  | .py       | Python script            |
| 001  | .json     | JSON config / data       |
| 010  | .yaml     | YAML config              |
| 011  | .bin      | Binary / compiled        |
| 100  | .md       | Markdown document        |
| 101  | .sh       | Shell script             |
| 110  | .cpp      | C / C++ source           |
| 111  | .txt      | Plain text / misc        |

### ROLE (bits 12–10) — Functional Identity

| Bits | Role         | Description                        |
|------|--------------|------------------------------------|
| 000  | orchestrator | Top-level coordinator / entry point|
| 001  | tool         | Callable tool / plugin             |
| 010  | config       | Configuration / settings           |
| 011  | data         | Data payload / dataset             |
| 100  | doc          | Documentation / reference          |
| 101  | test         | Test / benchmark                   |
| 110  | bridge       | Inter-system adapter               |
| 111  | ephemeral    | Temp / scratch / one-shot          |

### TIER (bits 9–8) — Execution Tier

| Bits | Tier    | Description                        |
|------|---------|------------------------------------|
| 00   | core    | System-critical, always loaded     |
| 01   | plugin  | Loadable extension                 |
| 10   | sandbox | Isolated / experimental            |
| 11   | archive | Frozen / versioned snapshot        |

### SEQUENCE (bits 7–0)

0–255 unique entries per type/role/tier combination.
Auto-assigned by the registry. Never manually set.

---

## Filename Format

```
{16-bit-binary-key}.{extension}

Examples:
  0000000000000001.py    → Python, orchestrator, core, seq 1
  0010010000000001.json  → JSON, config, core, seq 1
  1000100000000001.md    → Markdown, doc, core, seq 1
  0000010100000001.sh    → Shell, test, sandbox, seq 1
```

---

## Manifest Schema

All metadata lives in `gfs_manifest.json`. The filename is opaque.
The manifest is the truth layer.

```json
{
  "0000000000000001": {
    "key": "0000000000000001",
    "filename": "0000000000000001.py",
    "extension": "py",
    "type_id": 0,
    "role_id": 0,
    "tier_id": 0,
    "sequence": 1,
    "type": "Python script",
    "role": "orchestrator",
    "tier": "core",
    "description": "ADAP main orchestrator entry point",
    "blake3": "a3f1c2d4...",
    "created_at": "2026-05-06T00:00:00",
    "tags": ["adap", "production"]
  }
}
```

---

## AI Resolution Protocol

When an AI agent needs a file:

1. **Query manifest** by role + tier + extension
2. **Receive key** — single unambiguous result
3. **Construct filename** — `{key}.{ext}`
4. **Execute / load** — no naming interpretation required

No semantic parsing. No ambiguity. Deterministic every time.

---

## CLI Reference

```bash
python gfs_registry.py schema              # Print full encoding table
python gfs_registry.py decode <key>        # Decode a key to components
python gfs_registry.py register \
  --type 0 --role 0 --tier 0 \
  --desc "ADAP orchestrator" \
  --tags adap production \
  --file ./0000000000000001.py             # Register a file
python gfs_registry.py resolve <key>       # Look up a registered key
python gfs_registry.py query --role tool --tier core  # Filter registry
python gfs_registry.py list                # All entries
python gfs_registry.py remove <key>        # Remove entry
```

---

## Integration Points

- **GhostGoat**: Query GFS registry via role=`tool`, resolve key, execute
- **ADAP**: Boot sequence resolves role=`orchestrator`, tier=`core`
- **cogno**: Config resolution via role=`config`, tier=`core`
- **CI/CD**: Hash verification via `blake3` field before any execution

---

## Design Properties

| Property | Value |
|---|---|
| Collision resistance | Structural — same type/role/tier/seq → same key |
| AI parseability | O(1) decode — pure bitwise ops |
| Human readability | None required — manifest provides context |
| Extensibility | 65,536 slots; schema fields extensible via manifest |
| Integrity | Per-file SHA3-256 hash in manifest |
