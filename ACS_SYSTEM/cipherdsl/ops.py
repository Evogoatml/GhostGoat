# ops.py
from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto.Hash import SHA3_512, SHA512
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa
import base64, json, os, time

def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()

def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode())

# -------- keys (optional Ed25519 for signatures of envelopes) ----------
KEYS_DIR = ".keys"
PRIV = os.path.join(KEYS_DIR, "ed25519_priv.pem")
PUB  = os.path.join(KEYS_DIR, "ed25519_pub.pem")

def ensure_ed25519():
    os.makedirs(KEYS_DIR, exist_ok=True)
    if not (os.path.exists(PRIV) and os.path.exists(PUB)):
        key = ECC.generate(curve="Ed25519")
        with open(PRIV, "wt") as f: f.write(key.export_key(format="PEM"))
        with open(PUB,  "wt") as f: f.write(key.public_key().export_key(format="PEM"))
    return PRIV, PUB

def sign_json(obj: dict) -> str:
    ensure_ed25519()
    with open(PRIV, "rt") as f: sk = ECC.import_key(f.read())
    signer = eddsa.new(sk, mode="rfc8032")
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return b64e(signer.sign(blob))

def verify_json(obj: dict, sig_b64: str) -> bool:
    ensure_ed25519()
    with open(PUB, "rt") as f: pk = ECC.import_key(f.read())
    v = eddsa.new(pk, mode="rfc8032")
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    try:
        v.verify(blob, b64d(sig_b64))
        return True
    except Exception:
        return False

# -------- rolling key (evolves per counter + time) ---------------------
def rolling_key(prev_key: bytes, counter: int, extra: bytes = b"") -> bytes:
    h = SHA3_512.new(prev_key + counter.to_bytes(8, "big") + extra)
    return h.digest()[:32]  # 256-bit

# -------- AES-GCM ------------------------------------------------------
def aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b""):
    nonce = get_random_bytes(12)
    c = AES.new(key, AES.MODE_GCM, nonce=nonce)
    c.update(aad)
    ct, tag = c.encrypt_and_digest(plaintext)
    return dict(alg="AES-GCM", nonce=b64e(nonce), tag=b64e(tag), ct=b64e(ct), aad=b64e(aad))

def aes_gcm_decrypt(key: bytes, bundle: dict) -> bytes:
    nonce = b64d(bundle["nonce"]); tag = b64d(bundle["tag"])
    ct = b64d(bundle["ct"]); aad = b64d(bundle.get("aad", ""))
    c = AES.new(key, AES.MODE_GCM, nonce=nonce)
    c.update(aad)
    return c.decrypt_and_verify(ct, tag)

# -------- ChaCha20-Poly1305 -------------------------------------------
def chacha_encrypt(key: bytes, plaintext: bytes, aad: bytes = b""):
    nonce = get_random_bytes(12)
    c = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    c.update(aad)
    ct, tag = c.encrypt_and_digest(plaintext)
    return dict(alg="CHACHA20-POLY1305", nonce=b64e(nonce), tag=b64e(tag), ct=b64e(ct), aad=b64e(aad))

def chacha_decrypt(key: bytes, bundle: dict) -> bytes:
    nonce = b64d(bundle["nonce"]); tag = b64d(bundle["tag"])
    ct = b64d(bundle["ct"]); aad = b64d(bundle.get("aad", ""))
    c = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    c.update(aad)
    return c.decrypt_and_verify(ct, tag)

# -------- Whirlpool integrity (hash of final bytes) --------------------
def whirlpool_digest(data: bytes) -> str:
    h = SHA512.new(data)
    return h.hexdigest()
