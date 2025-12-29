# dsl.py
import os, yaml

class DSLParseError(Exception):
    pass

def load_pipeline(path: str) -> dict:
    with open(path, "rt") as f:
        cfg = yaml.safe_load(f)
    # expected shape:
    # name: EvolveX
    # key_source: env:EVOLVE_SEED | hex:... | random:32
    # steps: [{op: rolling_key, extra: time_ns}, {op: aes_gcm, aad: "adap"}, ... , {op: whirlpool}]
    if not isinstance(cfg, dict) or "steps" not in cfg:
        raise DSLParseError("Missing 'steps' in pipeline YAML.")
    cfg.setdefault("name", "unnamed")
    cfg.setdefault("meta", {})
    return cfg

def resolve_key_source(key_source: str) -> bytes:
    """
    Supports:
      - env:VAR_NAME
      - hex:0123abcd...
      - random:N   (N bytes)
    """
    if key_source.startswith("env:"):
        v = os.getenv(key_source.split(":",1)[1], "")
        if not v:
            raise DSLParseError(f"env var not set: {key_source}")
        return v.encode() if len(v) in (16,24,32) else v.encode().ljust(32, b"\0")[:32]
    if key_source.startswith("hex:"):
        hx = key_source.split(":",1)[1]
        b = bytes.fromhex(hx)
        return b.ljust(32, b"\0")[:32]
    if key_source.startswith("random:"):
        n = int(key_source.split(":",1)[1])
        import os as _os
        return _os.urandom(n).ljust(32, b"\0")[:32]
    raise DSLParseError(f"Unknown key_source: {key_source}")

