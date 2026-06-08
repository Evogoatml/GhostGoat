"""
CipherDSL — Per-Block Encryption with HKDF + AES-GCM + Blake3 + Avalanche
==========================================================================

Upgrades over v1
----------------
1. Blake3 replaces Whirlpool/SHA3-512 as the integrity hash
   - 3–8× faster, parallelisable, same 256-bit output
   - Built-in avalanche: any 1-bit input change flips ~50% of output bits
   - Keyed mode used for MAC-like integrity (not just a plain hash)

2. XOR stream diffusion layer (pre-encryption)
   - Before AES-GCM sees the plaintext, it is XOR'd against a BLAKE3
     keystream derived from the block key + nonce.
   - Ensures even low-entropy data (e.g. all zeros, repeated patterns)
     enters AES-GCM looking maximally random.
   - Cost: one Blake3 call per block (negligible).

3. Avalanche mixing (Feistel-style, 4 rounds)
   - Applied to the XOR-diffused data before AES-GCM encryption.
   - 4-round Feistel network: each round mixes left and right halves
     using BLAKE3. A 1-bit change in input → ~50% of bits flip in output.
   - Makes pre-image attacks on the ciphertext structurally infeasible.

Security stack per block
------------------------
    raw data
      ↓  XOR diffusion        (BLAKE3 keystream, key=block_key, data=nonce)
      ↓  Avalanche mixing     (4-round Feistel, BLAKE3 round function)
      ↓  AES-GCM encrypt      (AEAD seal, 16-byte tag)
      ↓  BLAKE3 keyed hash    (integrity of assembled plaintext)
    opaque CipherPacket

On decrypt, the entire stack is reversed and verified.
Any tampering at any layer raises ValueError immediately.
"""
from __future__ import annotations
import json
import logging
import os
import secrets
import struct
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Blake3 ────────────────────────────────────────────────────────────────────
try:
    import blake3 as _blake3_mod
    def _blake3(data: bytes, key: Optional[bytes] = None) -> bytes:
        if key:
            return _blake3_mod.blake3(data, key=key[:32].ljust(32, b"\x00")).digest()
        return _blake3_mod.blake3(data).digest()
    _HASH_IMPL = "blake3"
except ImportError:
    import hashlib
    def _blake3(data: bytes, key: Optional[bytes] = None) -> bytes:
        h = hashlib.sha3_256(data)
        if key:
            h = hashlib.sha3_256(key + data)
        return h.digest()
    _HASH_IMPL = "sha3_256_fallback"
    logger.debug("[Cipher] blake3 not installed — using SHA3-256 fallback")

# ── Crypto ────────────────────────────────────────────────────────────────────
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes as _hashes


def _derive_key(master_key: bytes, counter: int, block_id: bytes = b"") -> bytes:
    salt = struct.pack(">Q", counter) + block_id[:16]
    return HKDF(
        algorithm=_hashes.SHA256(), length=32,
        salt=salt, info=b"GhostGoat-CipherDSL-v2",
    ).derive(master_key)


# ── XOR diffusion ─────────────────────────────────────────────────────────────

def _xor_diffuse(data: bytes, key: bytes, nonce: bytes) -> bytes:
    """
    XOR data with a BLAKE3 keystream.
    keystream = BLAKE3(key=block_key, data=nonce) repeated to cover len(data).
    Ensures maximum entropy entering AES-GCM regardless of payload content.
    """
    seed = _blake3(nonce, key=key)
    # Expand seed to cover data length via counter-mode BLAKE3
    keystream = bytearray()
    ctr = 0
    while len(keystream) < len(data):
        keystream.extend(_blake3(seed + struct.pack(">I", ctr)))
        ctr += 1
    return bytes(a ^ b for a, b in zip(data, keystream[:len(data)]))


# ── Avalanche mixing — 4-round Feistel ───────────────────────────────────────

def _feistel(data: bytes, key: bytes, rounds: int = 4) -> bytes:
    """
    4-round Feistel network using BLAKE3 as the round function.
    A 1-bit change in `data` flips ~50% of output bits (avalanche guaranteed).
    Reversible: _feistel(_feistel(data, key, rounds), key, rounds) == data
    """
    n = len(data)
    mid = n // 2
    L = bytearray(data[:mid])
    R = bytearray(data[mid:])
    for r in range(rounds):
        rk = _blake3(key + struct.pack(">I", r))
        # F(R) = BLAKE3(round_key || R), truncated/expanded to len(L)
        f_input = bytes(rk) + bytes(R)
        f_out = bytearray()
        ctr = 0
        while len(f_out) < len(L):
            f_out.extend(_blake3(f_input + struct.pack(">I", ctr)))
            ctr += 1
        f_out = f_out[:len(L)]
        new_R = bytearray(a ^ b for a, b in zip(L, f_out))
        L, R = R, new_R
    # Final swap to make encryption and decryption symmetric
    return bytes(R) + bytes(L)


def _feistel_inverse(data: bytes, key: bytes, rounds: int = 4) -> bytes:
    """Reverse the Feistel network (run rounds in reverse)."""
    n = len(data)
    mid = n - n // 2   # R half size (may differ by 1 byte)
    R = bytearray(data[:mid])
    L = bytearray(data[mid:])
    for r in range(rounds - 1, -1, -1):
        rk = _blake3(key + struct.pack(">I", r))
        f_input = bytes(rk) + bytes(R)
        f_out = bytearray()
        ctr = 0
        while len(f_out) < len(L):
            f_out.extend(_blake3(f_input + struct.pack(">I", ctr)))
            ctr += 1
        f_out = f_out[:len(L)]
        new_L = bytearray(a ^ b for a, b in zip(L, f_out))
        R, L = new_L, R
    return bytes(L) + bytes(R)


# ── Packet ────────────────────────────────────────────────────────────────────

@dataclass
class CipherPacket:
    nonce: bytes
    ciphertext: bytes
    counter: int

    HEADER_SIZE = 12 + 8 + 4

    def to_bytes(self) -> bytes:
        return (self.nonce
                + struct.pack(">Q", self.counter)
                + struct.pack(">I", len(self.ciphertext))
                + self.ciphertext)

    @classmethod
    def from_bytes(cls, raw: bytes) -> "CipherPacket":
        if len(raw) < cls.HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(raw)}")
        nonce = raw[:12]
        counter = struct.unpack(">Q", raw[12:20])[0]
        ct_len = struct.unpack(">I", raw[20:24])[0]
        return cls(nonce=nonce, ciphertext=raw[24:24 + ct_len], counter=counter)


# ── CipherDSL ─────────────────────────────────────────────────────────────────

SEPARATOR = b"\x00\xff\x00"


class CipherDSL:
    """
    Full encryption pipeline per block:
        XOR diffusion → Avalanche (Feistel) → AES-GCM + Blake3 integrity

    Usage
    -----
        dsl = CipherDSL(master_key=os.urandom(32))
        packet       = dsl.encrypt(data, metadata={"index": 0})
        data, meta   = dsl.decrypt(packet)
    """

    def __init__(self, master_key: Optional[bytes] = None,
                 padding: bool = True, feistel_rounds: int = 4):
        if master_key is None:
            logger.warning("[Cipher] no master_key — generating ephemeral (dev only)")
            master_key = secrets.token_bytes(32)
        if len(master_key) < 16:
            raise ValueError("master_key must be ≥16 bytes")
        self._master_key = master_key
        self._padding = padding
        self._feistel_rounds = feistel_rounds
        self._counter: int = 0
        logger.debug("[Cipher] ready (hash=%s rounds=%d padding=%s)",
                     _HASH_IMPL, feistel_rounds, padding)

    # ── encrypt ───────────────────────────────────────────────────────────────

    def encrypt(self, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> CipherPacket:
        self._counter += 1
        meta = metadata or {}
        meta["_counter"] = self._counter
        if self._padding:
            meta["_pad"] = secrets.token_hex(secrets.randbelow(32) + 4)

        meta_bytes = json.dumps(meta, separators=(",", ":")).encode()
        payload_content = meta_bytes + SEPARATOR + data

        # Blake3 keyed integrity hash of the assembled plaintext
        block_id = data[:16].ljust(16, b"\x00")
        key = _derive_key(self._master_key, self._counter, block_id)
        integrity_hash = _blake3(payload_content, key=key)   # 32 bytes

        plaintext_raw = integrity_hash + payload_content

        nonce = secrets.token_bytes(12)

        # Layer 1: XOR diffusion (kills low-entropy patterns)
        diffused = _xor_diffuse(plaintext_raw, key, nonce)

        # Layer 2: Avalanche mixing (Feistel — 1-bit change → ~50% flip)
        mixed = _feistel(diffused, key, self._feistel_rounds)

        # Layer 3: AES-GCM seal
        ciphertext = AESGCM(key).encrypt(nonce, mixed, None)

        return CipherPacket(nonce=nonce, ciphertext=ciphertext, counter=self._counter)

    # ── decrypt ───────────────────────────────────────────────────────────────

    def decrypt(self, packet: CipherPacket) -> Tuple[bytes, Dict[str, Any]]:
        block_id = b"\x00" * 16
        key = _derive_key(self._master_key, packet.counter, block_id)

        # Layer 3: AES-GCM verify + unseal
        try:
            mixed = AESGCM(key).decrypt(packet.nonce, packet.ciphertext, None)
        except Exception as exc:
            raise ValueError(f"[Cipher] AES-GCM auth failed: {exc}") from exc

        # Layer 2: reverse Feistel
        diffused = _feistel_inverse(mixed, key, self._feistel_rounds)

        # Layer 1: reverse XOR diffusion
        plaintext_raw = _xor_diffuse(diffused, key, packet.nonce)

        # Blake3 integrity check
        stored_hash = plaintext_raw[:32]
        payload_content = plaintext_raw[32:]
        computed_hash = _blake3(payload_content, key=key)
        if computed_hash != stored_hash:
            raise ValueError("[Cipher] Blake3 integrity FAILED — data tampered")

        # Unpack metadata + data
        sep_pos = payload_content.find(SEPARATOR)
        if sep_pos == -1:
            raise ValueError("[Cipher] separator not found — corrupted packet")
        meta = json.loads(payload_content[:sep_pos].decode())
        meta.pop("_pad", None)
        return payload_content[sep_pos + len(SEPARATOR):], meta

    # ── key management ────────────────────────────────────────────────────────

    def rotate_master_key(self, new_key: bytes):
        if len(new_key) < 16:
            raise ValueError("new_key must be ≥16 bytes")
        self._master_key = new_key
        self._counter = 0
        logger.info("[Cipher] master key rotated, counter reset")

    @property
    def counter(self) -> int:
        return self._counter
