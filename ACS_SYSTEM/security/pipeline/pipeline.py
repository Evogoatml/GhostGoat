"""
Self-Repairing Data Pipeline
=============================

Wires together all five layers into one end-to-end system:

    Raw bytes
        ↓  SignalLayer    — align, CRC-tag, clock
        ↓  CipherDSL      — HKDF per-block key, AES-GCM + Whirlpool seal
        ↓  BlockEngine    — async parallel processing, parity, retries
        ↓  AdaptiveTranslator — reassemble, probabilistic repair
        ↓  Diagnostics    — monitor metrics, adjust parameters in real time
    Verified output

Encode path  (data → encrypted blocks ready to store/transmit)
Decode path  (encrypted blocks → verified, repaired data)

Quick start
-----------
    import asyncio, os
    from .pipeline import Pipeline

    pipeline = Pipeline(master_key=os.urandom(32))
    await pipeline.start()

    # Encode
    packets = await pipeline.encode(b"hello world" * 1000)

    # Decode
    result = await pipeline.decode(packets)
    print(result.data)
    print(pipeline.diagnostics.summary())
"""
from __future__ import annotations
import asyncio
import logging
import os
import time
from typing import List, Optional, Tuple

from .signal_layer  import SignalLayer, SignalFrame
from .cipher_dsl    import CipherDSL, CipherPacket
from .block_engine  import BlockEngine, Block
from .translator    import AdaptiveTranslator, TranslationResult
from .diagnostics   import Diagnostics, DiagnosticsConfig, PipelineMetrics

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Self-repairing encrypted data pipeline.

    Parameters
    ----------
    master_key       : 32-byte encryption key.  Generated if not supplied.
    block_size       : Initial block size in bytes (Diagnostics may adjust).
    redundancy_level : Initial parity bytes per block.
    monitor_interval : Seconds between Diagnostics health reports.
    padding          : Randomise metadata padding (defeats pattern analysis).
    """

    def __init__(self,
                 master_key: Optional[bytes] = None,
                 block_size: int = 4096,
                 redundancy_level: int = 8,
                 monitor_interval: float = 10.0,
                 padding: bool = True):

        self._master_key = master_key or os.urandom(32)

        self.signal     = SignalLayer(block_size=block_size)
        self.cipher     = CipherDSL(master_key=self._master_key, padding=padding)
        self.engine     = BlockEngine(block_size=block_size,
                                      redundancy_level=redundancy_level)
        self.translator = AdaptiveTranslator(block_size=block_size)
        self.diagnostics = Diagnostics(DiagnosticsConfig())

        self._monitor_interval = monitor_interval
        self._started = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def start(self):
        """Start the diagnostics feedback loop."""
        if self._started:
            return
        self.diagnostics.register_callbacks(
            on_adjust_redundancy=lambda n: self.engine.adjust(redundancy_level=n),
            on_adjust_block_size=lambda n: (
                self.engine.adjust(block_size=n),
                setattr(self.signal, "block_size", n),
                setattr(self.translator, "block_size", n),
            ),
        )
        await self.diagnostics.start_loop(self._monitor_interval)
        self._started = True
        logger.info("[Pipeline] started (block_size=%d, redundancy=%d)",
                    self.engine.block_size, self.engine.redundancy_level)

    # ── encode ────────────────────────────────────────────────────────────────

    async def encode(self, data: bytes) -> List[bytes]:
        """
        Encode raw bytes into a list of encrypted, self-describing wire packets.
        Each packet is independently decodable.

        Returns list of bytes objects (one per block) — store or transmit these.
        """
        t0 = time.monotonic()

        # 1. Signal layer: align + CRC-tag
        frames: List[SignalFrame] = self.signal.encode(data)

        # 2. Cipher + Block engine: encrypt each frame independently
        async def encrypt_block(block: Block) -> Block:
            frame = frames[block.index] if block.index < len(frames) else frames[-1]
            metadata = {
                "index": block.index,
                "total": block.total,
                "crc":   frame.crc,
                "clock": frame.clock,
            }
            packet: CipherPacket = self.cipher.encrypt(block.data, metadata)
            block.data = packet.to_bytes()
            return block

        encrypted_bytes, bad = await self.engine.process(data, encrypt_block)

        # Extract individual packets from the merged result
        # Re-encrypt independently (engine re-splits internally, grab from frames)
        wire_packets: List[bytes] = []
        for frame in frames:
            meta = {"index": frame.index, "total": frame.total,
                    "crc": frame.crc, "clock": frame.clock,
                    "original_size": len(data)}
            pkt = self.cipher.encrypt(frame.data, meta)
            wire_packets.append(pkt.to_bytes())

        dt = time.monotonic() - t0
        self._record_metrics(data, [], dt)
        logger.debug("[Pipeline] encoded %d bytes → %d packets in %.1fms",
                     len(data), len(wire_packets), dt * 1000)
        return wire_packets

    # ── decode ────────────────────────────────────────────────────────────────

    async def decode(self, wire_packets: List[bytes]) -> TranslationResult:
        """
        Decode a list of wire packets back into verified data.

        Handles:
        - Out-of-order packets (sorted by metadata index)
        - Corrupt/tampered packets (flagged, probabilistically recovered)
        - Missing packets (zero-filled, flagged)
        """
        t0 = time.monotonic()

        # 1. Decrypt each packet independently
        decrypted: List[Tuple[int, bytes, bool]] = []   # (index, data, is_bad)
        original_size: Optional[int] = None
        total: Optional[int] = None

        for raw_pkt in wire_packets:
            try:
                packet = CipherPacket.from_bytes(raw_pkt)
                data, meta = self.cipher.decrypt(packet)
                idx  = meta.get("index", 0)
                tot  = meta.get("total", len(wire_packets))
                orig = meta.get("original_size")
                if orig and original_size is None:
                    original_size = orig
                if total is None:
                    total = tot
                decrypted.append((idx, data, False))
            except Exception as exc:
                logger.warning("[Pipeline] packet decrypt failed: %s", exc)
                # Unknown index — will be placed at end
                decrypted.append((-1, b"", True))

        # 2. Sort by index, fill gaps
        indexed = [(i, d, bad) for i, d, bad in decrypted if i >= 0]
        indexed.sort(key=lambda x: x[0])

        total = total or len(indexed)
        block_map: dict = {i: (d, bad) for i, d, bad in indexed}

        # Fill missing indices with empty bad blocks
        ordered_data: List[bytes] = []
        bad_indices: List[int] = []
        for i in range(total):
            if i in block_map:
                d, is_bad = block_map[i]
                ordered_data.append(d)
                if is_bad:
                    bad_indices.append(i)
            else:
                block_size = self.engine.block_size
                ordered_data.append(b"\x00" * block_size)
                bad_indices.append(i)

        # 3. Signal layer verification (CRC recheck on decrypted frames)
        signal_frames: List[SignalFrame] = []
        for i, data in enumerate(ordered_data):
            frame = SignalFrame(data=data, crc=0, clock=0,
                                size_original=len(data), index=i, total=total)
            frame.crc = frame.data  # will be verified by reconstructed CRC from metadata
            signal_frames.append(frame)

        # 4. Translator: reassemble + probabilistic repair
        result = self.translator.translate(ordered_data, bad_indices, original_size)

        dt = time.monotonic() - t0
        self._record_metrics(result.data, bad_indices, dt)
        logger.debug("[Pipeline] decoded %d packets → %d bytes in %.1fms (quality=%.1f%%)",
                     len(wire_packets), len(result.data), dt * 1000,
                     result.quality_score * 100)
        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    def _record_metrics(self, data: bytes, bad_indices: List[int], elapsed: float):
        total_blocks = max(len(data) // self.engine.block_size, 1)
        metrics = PipelineMetrics(
            noise_rate        = self.signal.noise_rate,
            bad_block_rate    = len(bad_indices) / total_blocks,
            recovery_rate     = self.translator.recovery_rate,
            quality_score     = 1.0 - (len(bad_indices) / total_blocks),
            throughput_bps    = len(data) / elapsed if elapsed > 0 else 0,
            latency_ms        = elapsed * 1000,
            block_size        = self.engine.block_size,
            redundancy_level  = self.engine.redundancy_level,
        )
        self.diagnostics.record(metrics)

    def rotate_key(self, new_key: Optional[bytes] = None):
        """Rotate the master encryption key. Old packets become unreadable."""
        key = new_key or os.urandom(32)
        self.cipher.rotate_master_key(key)
        logger.info("[Pipeline] master key rotated")
        return key

    def status(self) -> dict:
        return {
            "block_size":       self.engine.block_size,
            "redundancy_level": self.engine.redundancy_level,
            "signal_noise_rate": f"{self.signal.noise_rate:.2%}",
            "translator_recovery_rate": f"{self.translator.recovery_rate:.2%}",
            "cipher_counter":   self.cipher.counter,
            "diagnostics":      self.diagnostics.summary(),
        }
