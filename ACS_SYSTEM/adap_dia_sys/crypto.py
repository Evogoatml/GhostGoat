#!/usr/bin/env python3
"""
Crypto primitives for GhostGoat adaptive vault.
Provides AEAD encryption (AES-GCM, ChaCha20-Poly1305) and Ed25519 signing.
"""
from __future__ import annotations

import os
import json
import base64
import logging
import sys
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


class CryptoError(Exception):
    """Base exception for crypto operations."""
    pass


class CryptoConfig:
    """Configuration for crypto operations."""
    keys_dir: str = "keys"
    default_cipher: str = "aesgcm"
    dry_run: bool = False


class GhostGoatCrypto:
    """AEAD encryption and Ed25519 signing primitives."""
    
    SUPPORTED_CIPHERS = {"aesgcm", "chacha20poly1305"}
    
    def __init__(self, config: Optional[CryptoConfig] = None):
        self.config = config or CryptoConfig()
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        self.logger = logging.getLogger("ghostgoat_crypto")
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def encrypt(
        self, 
        data: bytes, 
        cipher_name: Optional[str] = None
    ) -> tuple[bytes, bytes]:
        """
        Encrypt data with AEAD cipher.
        
        Returns:
            tuple of (ciphertext, nonce)
        """
        cipher_name = cipher_name or self.config.default_cipher
        
        if cipher_name not in self.SUPPORTED_CIPHERS:
            raise CryptoError(f"Unsupported cipher: {cipher_name}")
        
        key = os.urandom(32)
        nonce = os.urandom(12)
        
        if cipher_name == "aesgcm":
            cipher = AESGCM(key)
        else:
            cipher = ChaCha20Poly1305(key)
        
        ciphertext = cipher.encrypt(nonce, data, None)
        self.logger.debug(f"Encrypted {len(data)} bytes with {cipher_name}")
        
        return ciphertext, nonce
    
    def decrypt(
        self, 
        ciphertext: bytes, 
        nonce: bytes, 
        key: bytes,
        cipher_name: str = "aesgcm"
    ) -> bytes:
        """Decrypt data with AEAD cipher."""
        if cipher_name not in self.SUPPORTED_CIPHERS:
            raise CryptoError(f"Unsupported cipher: {cipher_name}")
        
        if cipher_name == "aesgcm":
            cipher = AESGCM(key)
        else:
            cipher = ChaCha20Poly1305(key)
        
        return cipher.decrypt(nonce, ciphertext, None)
    
    def generate_keypair(self) -> tuple[bytes, bytes]:
        """Generate Ed25519 keypair. Returns (private_key_bytes, public_key_bytes)."""
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes_raw()
        public_bytes = private_key.public_key().public_bytes_raw()
        return private_bytes, public_bytes
    
    def save_keypair(
        self, 
        private_path: Optional[str] = None,
        public_path: Optional[str] = None
    ) -> tuple[str, str]:
        """Generate and save Ed25519 keypair to files."""
        private_bytes, public_bytes = self.generate_keypair()
        
        private_path = private_path or os.path.join(self.config.keys_dir, "privkey.pem")
        public_path = public_path or os.path.join(self.config.keys_dir, "pubkey.pem")
        
        os.makedirs(self.config.keys_dir, exist_ok=True)
        
        if self.config.dry_run:
            self.logger.info(f"[DRY-RUN] Would save keypair to {private_path}, {public_path}")
            return private_path, public_path
        
        with open(private_path, "wb") as f:
            f.write(private_bytes)
        os.chmod(private_path, 0o600)
        
        with open(public_path, "wb") as f:
            f.write(public_bytes)
        
        self.logger.info(f"Saved keypair to {private_path}, {public_path}")
        return private_path, public_path
    
    def sign_log(
        self, 
        entry: dict, 
        privkey_path: Optional[str] = None
    ) -> dict:
        """Sign a log entry with Ed25519."""
        privkey_path = privkey_path or os.path.join(self.config.keys_dir, "privkey.pem")
        
        if not os.path.exists(privkey_path):
            raise CryptoError(f"Private key not found: {privkey_path}")
        
        with open(privkey_path, "rb") as f:
            private_key = Ed25519PrivateKey.from_private_bytes(f.read())
        
        payload = json.dumps(entry, sort_keys=True).encode()
        signature = private_key.sign(payload)
        
        entry["signature"] = base64.b64encode(signature).decode()
        self.logger.debug(f"Signed log entry")
        
        return entry
    
    def verify_signature(
        self, 
        entry: dict, 
        pubkey_path: Optional[str] = None
    ) -> bool:
        """Verify a signed log entry."""
        pubkey_path = pubkey_path or os.path.join(self.config.keys_dir, "pubkey.pem")
        
        if "signature" not in entry:
            return False
        
        if not os.path.exists(pubkey_path):
            self.logger.warning(f"Public key not found: {pubkey_path}")
            return False
        
        signature = base64.b64decode(entry["signature"])
        
        payload = json.dumps(
            {k: v for k, v in entry.items() if k != "signature"},
            sort_keys=True
        ).encode()
        
        with open(pubkey_path, "rb") as f:
            public_key = Ed25519PublicKey.from_public_bytes(f.read())
        
        try:
            public_key.verify(signature, payload)
            return True
        except Exception:
            return False


def main():
    """CLI entry point for key generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GhostGoat Crypto - Key Generation")
    parser.add_argument("--keys-dir", default="keys", help="Directory for keys")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    config = CryptoConfig(keys_dir=args.keys_dir, dry_run=args.dry_run)
    crypto = GhostGoatCrypto(config)
    
    priv_path, pub_path = crypto.save_keypair()
    print(f"Generated keypair:")
    print(f"  Private: {priv_path}")
    print(f"  Public:  {pub_path}")


if __name__ == "__main__":
    main()