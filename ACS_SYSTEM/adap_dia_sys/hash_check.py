#!/usr/bin/env python3
"""
Hash computation utilities.
Computes SHA256 hashes for file integrity verification.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def compute_sha256(path: str | Path) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        path: File path
    
    Returns:
        Hex digest string
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def verify_hash(path: str | Path, expected: str) -> bool:
    """Verify file hash matches expected."""
    try:
        actual = compute_sha256(path)
        return actual == expected
    except Exception:
        return False