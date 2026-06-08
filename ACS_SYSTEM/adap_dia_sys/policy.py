#!/usr/bin/env python3
"""
Policy engine for selecting ciphers based on system metrics.
"""
from __future__ import annotations

from typing import Any


def choose_cipher(metrics: dict[str, Any], mission: dict[str, Any]) -> str:
    """
    Choose cipher based on CPU load.
    
    Args:
        metrics: System metrics (cpu, memory, etc.)
        mission: Mission parameters (CPU_LIMIT, etc.)
    
    Returns:
        Cipher name: "chacha20poly1305" or "aesgcm"
    """
    cpu = metrics.get("cpu", 0)
    limit = int(mission.get("CPU_LIMIT", 60))
    
    if cpu > limit:
        return "chacha20poly1305"
    return "aesgcm"


def choose_cipher_safe(metrics: dict[str, Any], mission: dict[str, Any]) -> str:
    """Choose cipher with fallback/default."""
    try:
        return choose_cipher(metrics, mission)
    except Exception:
        return "aesgcm"  # Default to AES-GCM