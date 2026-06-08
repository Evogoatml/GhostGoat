"""
Signal Layer — Clocking, Alignment, CRC, and Manchester Encoding
================================================================

Upgrades over v1
----------------
- Manchester encoding on frame data before CRC
  Each byte is expanded to 2 bytes of transitions (0→10, 1→01).
  Self-clocking: the decoder finds bit boundaries from transitions alone.
  DC-balanced: equal 0s and 1s regardless of payload — kills baseline drift.
  Noise-immune: a random bit-flip changes a transition pair, caught immediately.

- Noise budget now tracks both CRC failures AND Manchester violations separately
  so Diagnostics can distinguish signal noise from data corruption.

Wire format (with Manchester)
-----------------------------
    header (21 bytes):
        crc(4) | clock(8) | size_original(4) | index(2) | total(2) | manchester_flag(1)
    body:
        manchester-encoded data (2× original size)

Manchester encoding rules
--------------------------
    bit 0  →  10  (high then low — falling edge)
    bit 1  →  01  (low then high — rising edge)
    Any other 2-bit pattern is invalid → noise detected, frame flagged corrupt.
"""
from __future__ import annotations
import struct
import zlib
import logging
from dataclasses import dataclass, field
from typing import List, Tuple

logger = logging.getLogger(__name__)

# ── CRC-32C ───────────────────────────────────────────────────────────────────
try:
    import crcmod
    _crc32c_fn = crcmod.predefined.mkCrcFun("crc-32c")
    def _crc32c(data: bytes) -> int:
        return _crc32c_fn(data)
except ImportError:
    def _crc32c(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF


# ── Manchester codec ──────────────────────────────────────────────────────────

def manchester_encode(data: bytes) -> bytes:
    """
    Encode bytes using Manchester encoding.
    Each input byte → 2 output bytes (16 transition bits for 8 data bits).
    Bit 0 → 0b10 (falling edge), Bit 1 → 0b01 (rising edge).
    Output is packed: 4 input bits → 1 output byte of 8 transition bits.
    """
    out = bytearray()
    for byte in data:
        # Process high nibble then low nibble, packing 4 Manchester pairs per byte
        for nibble_shift in (4, 0):
            nibble = (byte >> nibble_shift) & 0x0F
            encoded = 0
            for bit_pos in range(3, -1, -1):
                bit = (nibble >> bit_pos) & 1
                # 0 → 10 (bits 10 at positions 2i+1, 2i), 1 → 01
                encoded = (encoded << 2) | (0b10 if bit == 0 else 0b01)
            out.append(encoded)
    return bytes(out)


def manchester_decode(data: bytes) -> Tuple[bytes, int]:
    """
    Decode Manchester-encoded bytes back to original.
    Returns (decoded_bytes, violation_count).
    Violations are bit pairs that are neither 10 nor 01 (pure noise).
    """
    out = bytearray()
    violations = 0
    # Each pair of encoded bytes → one original byte
    for i in range(0, len(data) - 1, 2):
        hi_byte = data[i]
        lo_byte = data[i + 1]
        original = 0
        for encoded_byte in (hi_byte, lo_byte):
            nibble = 0
            for bit_pos in range(3, -1, -1):
                pair = (encoded_byte >> (bit_pos * 2)) & 0b11
                if pair == 0b10:
                    nibble = (nibble << 1) | 0
                elif pair == 0b01:
                    nibble = (nibble << 1) | 1
                else:
                    # Invalid transition — noise
                    violations += 1
                    nibble = (nibble << 1) | 0   # best-guess: 0
            original = (original << 4) | nibble
        out.append(original & 0xFF)
    return bytes(out), violations


# ── Frame ─────────────────────────────────────────────────────────────────────

HEADER_FMT = ">IQIHHB"   # crc(4) clock(8) size_orig(4) index(2) total(2) flags(1)
HEADER_SIZE = struct.calcsize(HEADER_FMT)   # 21 bytes

FLAG_MANCHESTER = 0x01


@dataclass
class SignalFrame:
    data: bytes           # always the raw (pre-Manchester) bytes
    crc: int
    clock: int
    size_original: int
    index: int = 0
    total: int = 1
    corrupted: bool = False
    manchester_violations: int = 0

    def verify(self) -> bool:
        computed = _crc32c(self.data)
        ok = computed == self.crc
        if not ok:
            self.corrupted = True
            logger.warning("[Signal] CRC mismatch frame %d/%d (got %08x expected %08x)",
                           self.index, self.total, computed, self.crc)
        return ok

    def to_bytes(self, use_manchester: bool = True) -> bytes:
        flags = FLAG_MANCHESTER if use_manchester else 0
        body = manchester_encode(self.data) if use_manchester else self.data
        header = struct.pack(HEADER_FMT,
                             self.crc, self.clock, self.size_original,
                             self.index, self.total, flags)
        return header + body

    @classmethod
    def from_bytes(cls, raw: bytes) -> "SignalFrame":
        if len(raw) < HEADER_SIZE:
            raise ValueError(f"Frame too short: {len(raw)}")
        crc, clock, size_original, index, total, flags = struct.unpack(
            HEADER_FMT, raw[:HEADER_SIZE])
        body = raw[HEADER_SIZE:]
        violations = 0
        if flags & FLAG_MANCHESTER:
            body, violations = manchester_decode(body)
        return cls(data=body, crc=crc, clock=clock, size_original=size_original,
                   index=index, total=total, manchester_violations=violations)


# ── Signal Layer ──────────────────────────────────────────────────────────────

class SignalLayer:
    """
    Splits raw bytes into Manchester-encoded, CRC-tagged frames.

    Usage
    -----
        sl = SignalLayer(block_size=4096, use_manchester=True)
        frames = sl.encode(raw_bytes)
        data, bad = sl.decode(frames)
    """

    def __init__(self, block_size: int = 4096, use_manchester: bool = True):
        self.block_size = block_size
        self.use_manchester = use_manchester
        self._clock: int = 0
        self._total_frames: int = 0
        self._bad_frames: int = 0
        self._total_violations: int = 0

    def encode(self, data: bytes) -> List[SignalFrame]:
        blocks = self._split(data)
        total = len(blocks)
        frames: List[SignalFrame] = []
        for i, block in enumerate(blocks):
            self._clock += 1
            frames.append(SignalFrame(
                data=block,
                crc=_crc32c(block),
                clock=self._clock,
                size_original=len(data) if i == total - 1 else len(block),
                index=i,
                total=total,
            ))
        logger.debug("[Signal] encoded %d bytes → %d frames (manchester=%s)",
                     len(data), total, self.use_manchester)
        return frames

    def encode_wire(self, data: bytes) -> List[bytes]:
        """Encode and serialise to wire bytes (with Manchester if enabled)."""
        return [f.to_bytes(self.use_manchester) for f in self.encode(data)]

    def decode(self, frames: List[SignalFrame]) -> Tuple[bytes, List[int]]:
        bad: List[int] = []
        ordered = sorted(frames, key=lambda f: f.index)
        parts: List[bytes] = []
        for frame in ordered:
            self._total_frames += 1
            self._total_violations += frame.manchester_violations
            if frame.manchester_violations > 0:
                logger.debug("[Signal] frame %d: %d Manchester violations (noise)",
                             frame.index, frame.manchester_violations)
            if not frame.verify():
                self._bad_frames += 1
                bad.append(frame.index)
                parts.append(b"\x00" * len(frame.data))
            else:
                parts.append(frame.data)
        raw = b"".join(parts)
        if ordered:
            raw = raw[:ordered[-1].size_original]
        logger.debug("[Signal] decoded %d frames → %d bytes (%d bad, %d violations)",
                     len(frames), len(raw), len(bad), self._total_violations)
        return raw, bad

    def decode_wire(self, wire_frames: List[bytes]) -> Tuple[bytes, List[int]]:
        """Deserialise wire bytes then decode."""
        frames = []
        for raw in wire_frames:
            try:
                frames.append(SignalFrame.from_bytes(raw))
            except Exception as e:
                logger.warning("[Signal] failed to parse frame: %s", e)
        return self.decode(frames)

    def _split(self, data: bytes) -> List[bytes]:
        blocks = []
        for i in range(0, len(data), self.block_size):
            block = data[i:i + self.block_size]
            if len(block) < self.block_size:
                block = block.ljust(self.block_size, b"\x00")
            blocks.append(block)
        return blocks or [b"\x00" * self.block_size]

    @property
    def noise_rate(self) -> float:
        if self._total_frames == 0:
            return 0.0
        return self._bad_frames / self._total_frames

    @property
    def violation_rate(self) -> float:
        """Manchester violation rate — pure electrical/signal noise indicator."""
        if self._total_frames == 0:
            return 0.0
        return self._total_violations / (self._total_frames * self.block_size * 8)

    def reset_stats(self):
        self._total_frames = 0
        self._bad_frames = 0
        self._total_violations = 0

    @property
    def clock(self) -> int:
        return self._clock
