# engine.py
import json, time
from typing import List, Dict, Any
from ops import (
    rolling_key, aes_gcm_encrypt, aes_gcm_decrypt,
    chacha_encrypt, chacha_decrypt, whirlpool_digest, sign_json, verify_json
)

class Context:
    def __init__(self, key: bytes):
        self.key = key
        self.counter = 0

def _normalize_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in steps:
        op = s.get("op","").lower()
        if op not in ("rolling_key","aes_gcm","chacha20","whirlpool"):
            raise ValueError(f"Unsupported op: {op}")
        out.append(s)
    return out

def encrypt_pipeline(name: str, meta: dict, ctx: Context, steps: List[Dict[str, Any]], plaintext: bytes) -> dict:
    steps = _normalize_steps(steps)
    payload = plaintext
    layers = []
    pipe_desc = []
    for s in steps:
        op = s["op"].lower()
        if op == "rolling_key":
            ctx.counter += 1
            extra = b""
            if s.get("extra") == "time_ns":
                extra = time.time_ns().to_bytes(8, "big")
            ctx.key = rolling_key(ctx.key, ctx.counter, extra)
            pipe_desc.append({"op":"rolling_key"})
        elif op == "aes_gcm":
            aad = (s.get("aad") or "").encode()
            bundle = aes_gcm_encrypt(ctx.key, payload, aad)
            payload = json.dumps(bundle, separators=(",", ":")).encode()
            layers.append(bundle); pipe_desc.append({"op":"aes_gcm"})
        elif op == "chacha20":
            aad = (s.get("aad") or "").encode()
            bundle = chacha_encrypt(ctx.key, payload, aad)
            payload = json.dumps(bundle, separators=(",", ":")).encode()
            layers.append(bundle); pipe_desc.append({"op":"chacha20"})
        elif op == "whirlpool":
            # integrity over current payload
            digest = whirlpool_digest(payload)
            pipe_desc.append({"op":"whirlpool","digest":digest})
        else:
            raise ValueError(f"Unknown op: {op}")

    envelope = {
        "name": name,
        "meta": meta or {},
        "pipeline": pipe_desc,         # order of ops
        "layers": layers,              # encryption layers in the order they were applied
        "blob": payload.decode() if isinstance(payload, (bytes, bytearray)) else payload
    }
    # optional signature of the envelope
    envelope["sig"] = sign_json({k: envelope[k] for k in ("name","meta","pipeline","layers","blob")})
    return envelope

def decrypt_pipeline(ctx: Context, envelope: dict) -> bytes:
    # verify signature if present (won't abort if missing)
    core = {k: envelope[k] for k in ("name","meta","pipeline","layers","blob")}
    if "sig" in envelope:
        ok = verify_json(core, envelope["sig"])
        if not ok:
            raise ValueError("Signature verification failed for envelope.")

    # rebuild key evolution across pipeline to mirror encryption
    payload = envelope["blob"].encode()
    layers = list(envelope["layers"])
    for p in envelope["pipeline"]:
        if p["op"] == "rolling_key":
            ctx.counter += 1
            ctx.key = rolling_key(ctx.key, ctx.counter, b"")  # time_ns can’t be replayed; keep deterministic
        elif p["op"] in ("aes_gcm","chacha20","whirlpool"):
            # we defer crypto ops until reverse walk
            pass

    # reverse through layers: last crypto op applied is first to remove
    for p in reversed(envelope["pipeline"]):
        if p["op"] == "chacha20":
            bundle = json.loads(payload.decode())
            payload = chacha_decrypt(ctx.key, bundle)
        elif p["op"] == "aes_gcm":
            bundle = json.loads(payload.decode())
            payload = aes_gcm_decrypt(ctx.key, bundle)
        elif p["op"] == "whirlpool":
            # integrity check (if present)
            digest = p.get("digest")
            if digest:
                from ops import whirlpool_digest
                if whirlpool_digest(payload) != digest:
                    raise ValueError("Whirlpool integrity mismatch.")
        elif p["op"] == "rolling_key":
            # no direct revert for rolling key; we already evolved key forward deterministically
            pass
    return payload
