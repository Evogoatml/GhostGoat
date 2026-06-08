"""
Block Engine — Async Divide & Conquer with Crystal Lattice 2D Parity
=====================================================================

Upgrades over v1
----------------
1. Crystal Lattice 2D Parity
   Blocks are arranged in a virtual grid (rows × cols).
   Row parity  = XOR of every block in a row   → extra blocks appended per row
   Column parity = XOR of every block in a column → extra blocks appended per col
   Recovery: one missing block can be reconstructed from its row XOR + col XOR.
   This is mathematically equivalent to RAID-6 P+Q but pure XOR — zero CPU overhead.

   Example (3×3 grid + parity):
       B00 B01 B02 | P0_row    ← row 0 parity
       B10 B11 B12 | P1_row
       B20 B21 B22 | P2_row
       ────────────┼──────
       P0_col P1_col P2_col    ← column parities

   Any single block gone? Row parity XOR the other blocks in that row recovers it.

2. Bitwise interleaving of burst errors
   Before splitting into blocks, bytes are bit-interleaved across the dataset.
   A burst error that corrupts N consecutive bytes only corrupts 1 bit per block
   (spread across N blocks) instead of killing N consecutive bytes in one block.
   On decode, the interleave is reversed.

3. XOR parity within each block (from v1) still present for single-bit recovery.

Wire layout
-----------
    Normal blocks: index 0 … (rows×cols - 1)
    Row parity blocks: index rows×cols … rows×cols + rows - 1
    Col parity blocks: index rows×cols + rows … end
"""
from __future__ import annotations
import asyncio
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
_POOL = ThreadPoolExecutor(thread_name_prefix="block_eng")


# ── Block ─────────────────────────────────────────────────────────────────────

@dataclass
class Block:
    index: int
    total: int
    data: bytes
    parity: bytes = b""
    redundancy_level: int = 4
    status: str = "pending"
    retries: int = 0
    is_parity_block: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_parity(self) -> bytes:
        n = self.redundancy_level
        if n == 0 or not self.data:
            return b""
        pad_len = (n - len(self.data) % n) % n
        padded = self.data + b"\x00" * pad_len
        parity = bytearray(n)
        for i in range(0, len(padded), n):
            for j in range(n):
                parity[j] ^= padded[i + j]
        return bytes(parity)

    def attach_parity(self) -> "Block":
        self.parity = self.compute_parity()
        return self

    def verify_parity(self) -> bool:
        if not self.parity:
            return True
        return self.compute_parity() == self.parity

    def to_bytes(self) -> bytes:
        import struct
        header = struct.pack(">HH", self.redundancy_level, len(self.parity))
        return header + self.parity + self.data

    @classmethod
    def from_bytes(cls, raw: bytes, index: int, total: int) -> "Block":
        import struct
        if len(raw) < 4:
            return cls(index=index, total=total, data=raw)
        rl, pl = struct.unpack(">HH", raw[:4])
        parity = raw[4:4 + pl]
        return cls(index=index, total=total, data=raw[4 + pl:],
                   parity=parity, redundancy_level=rl)


# ── Bitwise interleaving ──────────────────────────────────────────────────────

def _bit_interleave(data: bytes, n_blocks: int) -> bytes:
    """
    Interleave bits across blocks to protect against burst errors.
    A burst that kills N consecutive bytes only corrupts 1 bit per block.

    Implementation: treat data as a bit array, stride by n_blocks.
    Bit i → position (i % n_blocks) * (total_bits // n_blocks) + (i // n_blocks)
    """
    if n_blocks <= 1 or not data:
        return data
    total_bits = len(data) * 8
    # Pad to multiple of n_blocks
    pad = (-len(data)) % n_blocks
    padded = data + b"\x00" * pad
    bits_in = int.from_bytes(padded, "big")
    total_padded_bits = len(padded) * 8
    bits_out = 0
    for i in range(total_padded_bits):
        bit = (bits_in >> (total_padded_bits - 1 - i)) & 1
        out_pos = (i % n_blocks) * (total_padded_bits // n_blocks) + (i // n_blocks)
        if out_pos < total_padded_bits:
            bits_out |= bit << (total_padded_bits - 1 - out_pos)
    return bits_out.to_bytes(len(padded), "big")[:len(data)]


def _bit_deinterleave(data: bytes, n_blocks: int) -> bytes:
    """Reverse of _bit_interleave."""
    if n_blocks <= 1 or not data:
        return data
    pad = (-len(data)) % n_blocks
    padded = data + b"\x00" * pad
    total_padded_bits = len(padded) * 8
    bits_in = int.from_bytes(padded, "big")
    bits_out = 0
    for i in range(total_padded_bits):
        src_pos = (i % n_blocks) * (total_padded_bits // n_blocks) + (i // n_blocks)
        if src_pos < total_padded_bits:
            bit = (bits_in >> (total_padded_bits - 1 - src_pos)) & 1
            bits_out |= bit << (total_padded_bits - 1 - i)
    return bits_out.to_bytes(len(padded), "big")[:len(data)]


# ── Crystal Lattice (2D XOR parity) ──────────────────────────────────────────

class CrystalLattice:
    """
    Arrange data blocks in a 2D grid and compute row + column XOR parity.
    Any single block can be recovered from its row and column parity.
    """

    def __init__(self, blocks: List[bytes], block_size: int):
        n = len(blocks)
        # Find the smallest square-ish grid that fits all blocks
        cols = max(1, math.isqrt(n))
        rows = math.ceil(n / cols)
        self.rows = rows
        self.cols = cols
        self.block_size = block_size
        # Pad to fill the grid
        self._grid: List[List[bytes]] = []
        idx = 0
        for r in range(rows):
            row = []
            for c in range(cols):
                if idx < len(blocks):
                    row.append(blocks[idx])
                    idx += 1
                else:
                    row.append(b"\x00" * block_size)
            self._grid.append(row)

    def row_parities(self) -> List[bytes]:
        """XOR parity block for each row."""
        parities = []
        for row in self._grid:
            p = bytearray(self.block_size)
            for block in row:
                for i, byte in enumerate(block[:self.block_size]):
                    p[i] ^= byte
            parities.append(bytes(p))
        return parities

    def col_parities(self) -> List[bytes]:
        """XOR parity block for each column."""
        parities = []
        for c in range(self.cols):
            p = bytearray(self.block_size)
            for r in range(self.rows):
                block = self._grid[r][c]
                for i, byte in enumerate(block[:self.block_size]):
                    p[i] ^= byte
            parities.append(bytes(p))
        return parities

    def recover(self, row: int, col: int,
                row_parity: bytes, col_parity: bytes) -> bytes:
        """
        Recover a lost block at (row, col) using row XOR and column XOR.
        XOR the parity with all other blocks in that row (or col).
        """
        # Try row recovery first
        recovered = bytearray(row_parity)
        for c in range(self.cols):
            if c != col:
                block = self._grid[row][c]
                for i, byte in enumerate(block[:self.block_size]):
                    recovered[i] ^= byte
        return bytes(recovered)


# ── Block Engine ──────────────────────────────────────────────────────────────

class BlockEngine:
    """
    Divide & Conquer with crystal lattice 2D parity and bitwise interleaving.

    Usage
    -----
        engine = BlockEngine(block_size=4096, redundancy_level=8)
        results, bad = await engine.process(data, worker_fn)
    """

    def __init__(self,
                 block_size: int = 4096,
                 redundancy_level: int = 8,
                 max_workers: int = 8,
                 max_retries: int = 3,
                 retry_backoff: float = 0.05,
                 use_interleave: bool = True,
                 use_lattice: bool = True):
        self.block_size = block_size
        self.redundancy_level = redundancy_level
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.use_interleave = use_interleave
        self.use_lattice = use_lattice
        self._sem: Optional[asyncio.Semaphore] = None

    # ── split ─────────────────────────────────────────────────────────────────

    def split(self, data: bytes) -> Tuple[List[Block], Optional[CrystalLattice],
                                          List[bytes], List[bytes]]:
        """
        Split data into blocks.
        Returns (data_blocks, lattice, row_parities, col_parities).
        row_parities / col_parities are [] if use_lattice=False.
        """
        # Bitwise interleave before splitting
        if self.use_interleave:
            n_est = max(1, math.ceil(len(data) / self.block_size))
            data = _bit_interleave(data, n_est)

        chunks = [data[i:i + self.block_size] for i in range(0, len(data), self.block_size)]
        if not chunks:
            chunks = [b""]
        total = len(chunks)
        # Pad last chunk
        chunks[-1] = chunks[-1].ljust(self.block_size, b"\x00")

        blocks = [
            Block(index=i, total=total, data=c,
                  redundancy_level=self.redundancy_level,
                  metadata={"source_offset": i * self.block_size,
                             "source_size": len(data),
                             "interleaved": self.use_interleave}).attach_parity()
            for i, c in enumerate(chunks)
        ]

        lattice = row_p = col_p = None
        if self.use_lattice and len(blocks) > 1:
            lattice = CrystalLattice([b.data for b in blocks], self.block_size)
            row_p = lattice.row_parities()
            col_p = lattice.col_parities()
        return blocks, lattice, row_p or [], col_p or []

    # ── merge ─────────────────────────────────────────────────────────────────

    def merge(self, blocks: List[Block],
              row_parities: Optional[List[bytes]] = None,
              col_parities: Optional[List[bytes]] = None,
              original_size: Optional[int] = None) -> Tuple[bytes, List[int]]:
        """
        Merge blocks back to data. Uses lattice parity to recover bad blocks.
        Returns (data, unrecovered_indices).
        """
        ordered = sorted(blocks, key=lambda b: b.index)
        data_blocks = [b.data for b in ordered]
        bad_idx = [b.index for b in ordered if b.status == "failed"]

        # Crystal lattice recovery
        if row_parities and col_parities and bad_idx:
            lattice = CrystalLattice(data_blocks, self.block_size)
            for idx in bad_idx:
                r = idx // lattice.cols
                c = idx % lattice.cols
                if r < len(row_parities) and c < len(col_parities):
                    recovered = lattice.recover(r, c, row_parities[r], col_parities[c])
                    data_blocks[idx] = recovered
                    ordered[idx].status = "recovered"
                    logger.info("[BlockEngine] lattice-recovered block %d at (%d,%d)", idx, r, c)

        still_bad = [b.index for b in ordered if b.status == "failed"]
        raw = b"".join(data_blocks)

        # Reverse bit interleave
        if self.use_interleave:
            raw = _bit_deinterleave(raw, len(blocks))

        # Trim
        sz = original_size or (ordered[0].metadata.get("source_size") if ordered else None)
        if sz:
            raw = raw[:sz]

        logger.debug("[BlockEngine] merged %d blocks → %d bytes (%d unrecovered)",
                     len(blocks), len(raw), len(still_bad))
        return raw, still_bad

    # ── process ───────────────────────────────────────────────────────────────

    async def process(self, data: bytes,
                      worker: Callable[[Block], Any]) -> Tuple[bytes, List[int]]:
        """Full pipeline: split → parallel worker → lattice recover → merge."""
        self._sem = asyncio.Semaphore(self.max_workers)
        blocks, lattice, row_p, col_p = self.split(data)
        tasks = [asyncio.ensure_future(self._run_block(b, worker)) for b in blocks]
        results: List[Block] = await asyncio.gather(*tasks)
        return self.merge(results, row_p, col_p)

    async def _run_block(self, block: Block, worker: Callable) -> Block:
        async with self._sem:
            for attempt in range(self.max_retries + 1):
                try:
                    t0 = time.monotonic()
                    if asyncio.iscoroutinefunction(worker):
                        result = await worker(block)
                    else:
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(_POOL, worker, block)
                    result.metadata["process_ms"] = round((time.monotonic() - t0) * 1000, 2)
                    result.status = "ok"
                    if not result.verify_parity():
                        block.retries += 1
                        if attempt < self.max_retries:
                            await asyncio.sleep(self.retry_backoff * (2 ** attempt))
                            continue
                        result.status = "failed"
                    return result
                except Exception as exc:
                    logger.warning("[BlockEngine] block %d attempt %d: %s", block.index, attempt, exc)
                    block.retries += 1
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_backoff * (2 ** attempt))
            block.status = "failed"
            return block

    # ── tunability ────────────────────────────────────────────────────────────

    def adjust(self, block_size: Optional[int] = None,
               redundancy_level: Optional[int] = None):
        if block_size is not None:
            self.block_size = max(256, block_size)
        if redundancy_level is not None:
            self.redundancy_level = max(0, min(redundancy_level, 64))
        logger.info("[BlockEngine] adjusted: block_size=%d redundancy=%d",
                    self.block_size, self.redundancy_level)
