
from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA3_512
from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa
import base64, os, json

KEYS_DIR = "adap/keys"
PRIV = f"{KEYS_DIR}/privkey.pem"
PUB  = f"{KEYS_DIR}/pubkey.pem"

def _b64(x: bytes) -> str:
    return base64.b64encode(x).decode()

# ---------- Keygen (Ed25519) ----------
def ensure_keys():
    os.makedirs(KEYS_DIR, exist_ok=True)
    if not (os.path.exists(PRIV) and os.path.exists(PUB)):
        key = ECC.generate(curve="Ed25519")
        with open(PRIV, "wt") as f: f.write(key.export_key(format="PEM"))
        with open(PUB,  "wt") as f: f.write(key.public_key().export_key(format="PEM"))
    return PRIV, PUB

# ---------- AES-GCM ----------
def aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b""):
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(aad)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    return {"alg":"AES-GCM","nonce":_b64(nonce),"tag":_b64(tag),"ct":_b64(ct),"aad":_b64(aad)}

def aes_gcm_decrypt(key: bytes, bundle: dict) -> bytes:
    nonce = base64.b64decode(bundle["nonce"])
    tag   = base64.b64decode(bundle["tag"])
    ct    = base64.b64decode(bundle["ct"])
    aad   = base64.b64decode(bundle.get("aad",""))
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(aad)
    return cipher.decrypt_and_verify(ct, tag)

# ---------- ChaCha20-Poly1305 ----------
def chacha_encrypt(key: bytes, plaintext: bytes, aad: bytes = b""):
    nonce = get_random_bytes(12)
    cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    cipher.update(aad)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    return {"alg":"ChaCha20-Poly1305","nonce":_b64(nonce),"tag":_b64(tag),"ct":_b64(ct),"aad":_b64(aad)}

def chacha_decrypt(key: bytes, bundle: dict) -> bytes:
    nonce = base64.b64decode(bundle["nonce"])
    tag   = base64.b64decode(bundle["tag"])
    ct    = base64.b64decode(bundle["ct"])
    aad   = base64.b64decode(bundle.get("aad",""))
    cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    cipher.update(aad)
    return cipher.decrypt_and_verify(ct, tag)

# ---------- Rolling key (SHA3-512) ----------
def rolling_key(prev_key: bytes, counter: int, extra: bytes = b"") -> bytes:
    h = SHA3_512.new(prev_key + counter.to_bytes(8,"big") + extra)
    return h.digest()[:32]  # 256-bit

# ---------- Sign / Verify (Ed25519, RFC8032) ----------
def sign_json(obj: dict) -> str:
    ensure_keys()
    with open(PRIV,"rt") as f: sk = ECC.import_key(f.read())
    signer = eddsa.new(sk, mode="rfc8032")
    blob = json.dumps(obj, sort_keys=True).encode()
    sig = signer.sign(blob)
    return base64.b64encode(sig).decode()

def verify_json(obj: dict, b64sig: str) -> bool:
    ensure_keys()
    with open(PUB,"rt") as f: pk = ECC.import_key(f.read())
    vrf = eddsa.new(pk, mode="rfc8032")
    blob = json.dumps(obj, sort_keys=True).encode()
    try:
        vrf.verify(blob, base64.b64decode(b64sig))
        return True
    except Exception:
        return False
