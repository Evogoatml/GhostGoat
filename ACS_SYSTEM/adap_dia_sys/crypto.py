from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import os, json, base64

def encrypt(data: bytes, cipher_name: str) -> bytes:
    key = os.urandom(32)
    nonce = os.urandom(12)
    cipher = AESGCM(key) if cipher_name == "aesgcm" else ChaCha20Poly1305(key)
    return cipher.encrypt(nonce, data, None)

def sign_log(entry: dict, privkey_path="keys/privkey.pem"):
    with open(privkey_path, "rb") as keyfile:
        private_key = Ed25519PrivateKey.from_private_bytes(keyfile.read())
    payload = json.dumps(entry, sort_keys=True).encode()
    signature = private_key.sign(payload)
    entry["signature"] = base64.b64encode(signature).decode()
    return entry
