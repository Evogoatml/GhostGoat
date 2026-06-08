
import os, json, base64
from adap.agent_core.crypto_core import aes_gcm_encrypt, aes_gcm_decrypt
from adap.agent_core.rolling_code import RollingEngine

VAULT_PATH = "adap/data/vault/memory.json"
KEY_FILE   = "adap/keys/vault.key"

def _load_key():
    if not os.path.exists(KEY_FILE):
        k = os.urandom(32)
        with open(KEY_FILE, "wb") as f: f.write(k)
    else:
        with open(KEY_FILE, "rb") as f: k = f.read()
    return k

def store(obj):
    key = _load_key()
    enc = aes_gcm_encrypt(key, json.dumps(obj).encode())
    os.makedirs(os.path.dirname(VAULT_PATH), exist_ok=True)
    with open(VAULT_PATH, "w") as f:
        json.dump(enc, f, indent=2)
    return True

def load():
    key = _load_key()
    if not os.path.exists(VAULT_PATH):
        return {}
    with open(VAULT_PATH) as f:
        enc = json.load(f)
    data = aes_gcm_decrypt(key, enc)
    return json.loads(data)

def append(entry):
    data = load()
    if "records" not in data:
        data["records"] = []
    data["records"].append(entry)
    store(data)
    return len(data["records"])

def export_base64():
    if not os.path.exists(VAULT_PATH): return ""
    with open(VAULT_PATH,"rb") as f:
        return base64.b64encode(f.read()).decode()
