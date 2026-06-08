"""
Encrypted memory vault.

Relocated from empire/AgentGPT's memory_vault.py plugin.
AES-256-GCM encrypted JSON storage for sensitive agent data.

Stripped of hardcoded paths — caller provides storage location.
Uses the cryptography library instead of PyCryptodome for consistency
with GhostGoat's existing crypto stack (ACS_SYSTEM).
"""

import base64
import json
import logging
import os
import secrets
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EncryptedVault:
    """AES-256-GCM encrypted JSON key-value store.

    Data is encrypted at rest. The encryption key is stored separately
    from the vault file.

    Usage:
        vault = EncryptedVault(vault_dir="/path/to/data")
        vault.store({"api_keys": ["sk-..."], "secrets": {...}})
        data = vault.load()
        vault.append("records", {"event": "login", "ts": 12345})
    """

    def __init__(self, vault_dir: str = "data/vault"):
        self._vault_dir = vault_dir
        self._key_path = os.path.join(vault_dir, ".vault.key")
        self._data_path = os.path.join(vault_dir, "vault.enc")

    def store(self, obj: Any) -> None:
        """Encrypt and persist a JSON-serializable object."""
        key = self._load_or_create_key()
        data = json.dumps(obj).encode()

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise ImportError("cryptography library required. Run: pip install cryptography")

        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)

        envelope = {
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }

        os.makedirs(self._vault_dir, exist_ok=True)
        with open(self._data_path, "w") as f:
            json.dump(envelope, f)
        logger.debug("Vault data encrypted and stored.")

    def load(self) -> Any:
        """Decrypt and return stored data, or empty dict if no vault exists."""
        if not os.path.exists(self._data_path):
            return {}

        key = self._load_or_create_key()

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise ImportError("cryptography library required. Run: pip install cryptography")

        with open(self._data_path) as f:
            envelope = json.load(f)

        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ciphertext"])

        aesgcm = AESGCM(key)
        data = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(data.decode())

    def append(self, key: str, entry: Any) -> int:
        """Append an entry to a list stored under the given key.

        Returns the index of the new entry.
        """
        vault = self.load() or {}
        vault.setdefault(key, []).append(entry)
        self.store(vault)
        return len(vault[key]) - 1

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the vault by key."""
        vault = self.load() or {}
        return vault.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the vault by key."""
        vault = self.load() or {}
        vault[key] = value
        self.store(vault)

    def _load_or_create_key(self) -> bytes:
        """Load or generate a 256-bit AES key."""
        os.makedirs(self._vault_dir, exist_ok=True)
        if os.path.exists(self._key_path):
            with open(self._key_path, "rb") as f:
                return f.read()

        key = secrets.token_bytes(32)
        with open(self._key_path, "wb") as f:
            f.write(key)

        # Restrict key file permissions
        try:
            os.chmod(self._key_path, 0o600)
        except OSError:
            pass

        logger.info("Generated new vault encryption key.")
        return key
