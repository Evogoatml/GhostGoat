import os, json, base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

KEY_PATH = "adap/keys/vault.key"
VAULT_PATH = "adap/data/vault/memory.json"

def _load_key():
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    if not os.path.exists(KEY_PATH):
        key = get_random_bytes(32)
        with open(KEY_PATH, "wb") as f:
            f.write(key)
    else:
        with open(KEY_PATH, "rb") as f:
            key = f.read()
    return key

def store(obj):
    key = _load_key()
    data = json.dumps(obj).encode()
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    out = {
        "nonce": base64.b64encode(cipher.nonce).decode(),
        "tag": base64.b64encode(tag).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }
    os.makedirs(os.path.dirname(VAULT_PATH), exist_ok=True)
    with open(VAULT_PATH, "w") as f:
        json.dump(out, f)

def load():
    key = _load_key()
    if not os.path.exists(VAULT_PATH):
        return {"records": []}
    with open(VAULT_PATH) as f:
        out = json.load(f)
    nonce = base64.b64decode(out["nonce"])
    tag = base64.b64decode(out["tag"])
    ciphertext = base64.b64decode(out["ciphertext"])
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    data = cipher.decrypt_and_verify(ciphertext, tag)
    return json.loads(data.decode())

def append(entry):
    vault = load()
    vault.setdefault("records", []).append(entry)
    store(vault)
    return len(vault["records"]) - 1

def export_base64():
    with open(VAULT_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()
