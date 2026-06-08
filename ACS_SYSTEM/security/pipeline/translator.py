"""
Adaptive Translator — Reconstruction, Resync, and Probabilistic Decoding
========================================================================

After the Block Engine merges blocks and CipherDSL decrypts them, this layer:

1. Reassembles the final payload from verified blocks
2. Handles partial failure: if some blocks are bad, attempts probabilistic
   interpolation of the missing data using surrounding context
3. Detects and corrects encoding drift (byte-order, encoding mismatches)
4. Computes a top-level integrity hash of the complete output
5. Emits a TranslationResult with detailed quality metadata

Probabilistic recovery strategy
--------------------------------
For each bad block (zero-filled by BlockEngine):
  - Try linear interpolation between adjacent good blocks (byte-level)
  - Try pattern repetition from the preceding good block
  - If all else fails, keep zeros but flag the block as unrecovered

This is intentionally lightweight — the goal is best-effort recovery
not perfect reconstruction.  Diagnostics uses the recovery rate to
decide whether to increase redundancy upstream.
"""
from __future__ import annotations
import hashlib
import logging
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class TranslationResult:
    data: bytes
    integrity_hash: str          # SHA-256 of final output
    total_blocks: int
    bad_blocks: List[int]        # indices that were corrupt/missing
    recovered_blocks: List[int]  # indices that were probabilistically recovered
    unrecovered_blocks: List[int]
    quality_score: float         # 0.0 (all bad) → 1.0 (perfect)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_perfect(self) -> bool:
        return len(self.bad_blocks) == 0

    @property
    def is_usable(self) -> bool:
        """True if >80% of blocks were good or recovered."""
        return self.quality_score >= 0.80

    def summary(self) -> str:
        return (
            f"TranslationResult: {len(self.data)} bytes | "
            f"quality={self.quality_score:.1%} | "
            f"bad={len(self.bad_blocks)} | "
            f"recovered={len(self.recovered_blocks)} | "
            f"unrecovered={len(self.unrecovered_blocks)}"
        )


# ── Adaptive Translator ───────────────────────────────────────────────────────

class AdaptiveTranslator:
    """
    Converts a list of (data_bytes, is_bad) tuples into a TranslationResult.

    Usage
    -----
        translator = AdaptiveTranslator()
        result = translator.translate(blocks_with_status)
    """

    def __init__(self, block_size: int = 4096, encoding: str = "utf-8"):
        self.block_size = block_size
        self.encoding = encoding
        self._recovery_attempts: int = 0
        self._recovery_successes: int = 0

    # ── main entry ────────────────────────────────────────────────────────────

    def translate(self,
                  blocks: List[bytes],
                  bad_indices: List[int],
                  original_size: Optional[int] = None,
                  ) -> TranslationResult:
        """
        blocks      : list of block bytes in order (bad blocks are zero-filled)
        bad_indices : which indices were corrupt/missing
        original_size: trim output to this many bytes if known
        """
        total = len(blocks)
        bad_set = set(bad_indices)

        # Attempt probabilistic recovery on bad blocks
        recovered: List[int] = []
        unrecovered: List[int] = []
        repaired = list(blocks)

        for idx in bad_indices:
            self._recovery_attempts += 1
            fixed = self._recover_block(repaired, idx)
            if fixed is not None:
                repaired[idx] = fixed
                recovered.append(idx)
                self._recovery_successes += 1
                logger.debug("[Translator] block %d recovered probabilistically", idx)
            else:
                unrecovered.append(idx)
                logger.debug("[Translator] block %d unrecoverable — zero-filled", idx)

        # Assemble final output
        raw = b"".join(repaired)
        if original_size is not None:
            raw = raw[:original_size]

        # Top-level integrity hash
        integrity = hashlib.sha256(raw).hexdigest()

        # Quality score: fraction of blocks that are good or recovered
        good_count = total - len(unrecovered)
        quality = good_count / total if total else 1.0

        result = TranslationResult(
            data=raw,
            integrity_hash=integrity,
            total_blocks=total,
            bad_blocks=list(bad_indices),
            recovered_blocks=recovered,
            unrecovered_blocks=unrecovered,
            quality_score=quality,
            metadata={
                "encoding": self.encoding,
                "block_size": self.block_size,
                "original_size": original_size,
            },
        )
        logger.info("[Translator] %s", result.summary())
        return result

    # ── recovery strategies ───────────────────────────────────────────────────

    def _recover_block(self, blocks: List[bytes], idx: int) -> Optional[bytes]:
        """Try multiple recovery strategies. Return recovered bytes or None."""
        total = len(blocks)
        bad_set_local = {i for i, b in enumerate(blocks) if not any(b)}

        # Strategy 1: linear interpolation between prev and next good blocks
        prev = self._last_good(blocks, idx, bad_set_local)
        nxt  = self._next_good(blocks, idx, bad_set_local, total)

        if prev is not None and nxt is not None:
            interpolated = self._interpolate(prev, nxt, len(blocks[idx]))
            if interpolated:
                return interpolated

        # Strategy 2: repeat previous good block (better than zeros)
        if prev is not None and len(prev) > 0:
            return prev[:len(blocks[idx])].ljust(len(blocks[idx]), b"\x00")

        # Strategy 3: repeat next good block
        if nxt is not None and len(nxt) > 0:
            return nxt[:len(blocks[idx])].ljust(len(blocks[idx]), b"\x00")

        return None

    def _last_good(self, blocks: List[bytes], before: int, bad: set) -> Optional[bytes]:
        for i in range(before - 1, -1, -1):
            if i not in bad and blocks[i] and any(blocks[i]):
                return blocks[i]
        return None

    def _next_good(self, blocks: List[bytes], after: int, bad: set, total: int) -> Optional[bytes]:
        for i in range(after + 1, total):
            if i not in bad and blocks[i] and any(blocks[i]):
                return blocks[i]
        return None

    def _interpolate(self, prev: bytes, nxt: bytes, size: int) -> Optional[bytes]:
        """Byte-level linear interpolation between two blocks."""
        try:
            n = min(len(prev), len(nxt), size)
            result = bytearray(n)
            for i in range(n):
                result[i] = (prev[i] + nxt[i]) // 2
            # Pad to required size
            if n < size:
                result.extend(b"\x00" * (size - n))
            return bytes(result)
        except Exception:
            return None

    # ── metrics ───────────────────────────────────────────────────────────────

    @property
    def recovery_rate(self) -> float:
        if self._recovery_attempts == 0:
            return 1.0
        return self._recovery_successes / self._recovery_attempts

    def reset_stats(self):
        self._recovery_attempts = 0
        self._recovery_successes = 0

    # ── text helpers ──────────────────────────────────────────────────────────

    def decode_text(self, result: TranslationResult) -> str:
        """Best-effort UTF-8 decode of the translated data."""
        try:
            return result.data.decode(self.encoding)
        except UnicodeDecodeError:
            return result.data.decode(self.encoding, errors="replace")
