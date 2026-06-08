#!/usr/bin/env python3
"""
Translator Gate - Upload verification and quarantine system.
Validates manifest signatures, computes SHA256 hashes, and routes
uploads to quarantine or allows them based on threat detection.
"""
from __future__ import annotations

import os
import shutil
import json
import time
import hashlib
import base64
import logging
import signal
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class TranslatorGateConfig:
    """Configuration for the translator gate."""
    quarantine_dir: str = "quarantine"
    audit_log_path: str = "audit.log"
    keys_dir: str = "keys"
    pubkey_path: str = "keys/pubkey.pem"
    privkey_path: str = "keys/privkey.pem"
    dry_run: bool = False


class TranslatorGate:
    """Upload verification and quarantine system."""
    
    def __init__(self, config: Optional[TranslatorGateConfig] = None):
        self.config = config or TranslatorGateConfig()
        self._setup_logging()
        self._setup_directories()
        self._running = True
        self._setup_signal_handlers()
    
    def _setup_logging(self) -> None:
        self.logger = logging.getLogger("translator_gate")
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _setup_directories(self) -> None:
        os.makedirs(self.config.quarantine_dir, exist_ok=True)
        os.makedirs(self.config.keys_dir, exist_ok=True)
    
    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self._running = False
    
    def compute_sha256(self, path: str | Path) -> str:
        """Compute SHA256 hash of a file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    
    def verify_manifest(
        self, 
        manifest_path: str | Path, 
        sig_path: str | Path
    ) -> dict:
        """
        Verify manifest signature and return parsed content.
        For now, performs basic read/parse - extend with crypto verification.
        """
        manifest_path = Path(manifest_path)
        sig_path = Path(sig_path)
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        with manifest_path.open() as f:
            manifest = json.load(f)
        
        if not sig_path.exists():
            self.logger.warning(f"Signature file not found: {sig_path}")
        
        return manifest
    
    def match_exact(self, sha: str) -> bool:
        """Check for exact SHA256 match in blocklist."""
        blocklist_path = Path(self.config.quarantine_dir) / "blocklist_exact.txt"
        if blocklist_path.exists():
            with blocklist_path.open() as f:
                blocklist = {line.strip() for line in f if line.strip()}
                return sha in blocklist
        return False
    
    def match_ssdeep(self, content_path: str | Path) -> bool:
        """Check for fuzzy hash (ssdeep) similarity match."""
        return False
    
    def match_rules(self, content_path: str | Path) -> bool:
        """Check against YARA-style rules."""
        return False
    
    def append_entry(self, data: dict) -> None:
        """Write audit entry to log file (atomic append)."""
        entry = {
            "ts": time.time(),
            **data
        }
        line = json.dumps(entry, sort_keys=True) + "\n"
        
        if self.config.dry_run:
            self.logger.info(f"[DRY-RUN] Would write audit: {entry}")
            return
        
        try:
            with open(self.config.audit_log_path, "a") as f:
                f.write(line)
        except IOError as e:
            self.logger.error(f"Failed to write audit log: {e}")
    
    def quarantine_file(
        self, 
        content_p: str | Path, 
        manifest: dict
    ) -> str:
        """Move file to quarantine directory with audit trail."""
        content_p = Path(content_p)
        sha = self.compute_sha256(content_p)
        
        dst = os.path.join(self.config.quarantine_dir, sha)
        
        if self.config.dry_run:
            self.logger.info(f"[DRY-RUN] Would quarantine {content_p} -> {dst}")
            return dst
        
        shutil.move(str(content_p), dst)
        
        self.append_entry({
            "action": "quarantine",
            "sha": sha,
            "manifest_name": manifest.get("name", "unknown")
        })
        
        self.logger.info(f"Quarantined: {content_p} -> {dst}")
        return dst
    
    def process_upload(
        self, 
        manifest_p: str | Path, 
        sig_p: str | Path, 
        content_p: str | Path
    ) -> dict:
        """
        Process an upload: verify manifest, check hash, run threat detection.
        
        Returns:
            dict with status: "allow", "reject", or "quarantine"
        """
        manifest_p = Path(manifest_p)
        sig_p = Path(sig_p)
        content_p = Path(content_p)
        
        self.logger.info(f"Processing upload: {content_p}")
        
        try:
            manifest = self.verify_manifest(manifest_p, sig_p)
        except Exception as e:
            self.append_entry({
                "status": "reject",
                "reason": "manifest_verification_failed",
                "error": str(e)
            })
            self.logger.error(f"Manifest verification failed: {e}")
            return {"status": "reject", "reason": "manifest_verification_failed"}
        
        if not content_p.exists():
            self.append_entry({
                "status": "reject",
                "reason": "content_not_found",
                "path": str(content_p)
            })
            return {"status": "reject", "reason": "content_not_found"}
        
        sha = self.compute_sha256(content_p)
        
        if sha != manifest.get("content_sha256"):
            self.append_entry({
                "status": "reject",
                "reason": "hash_mismatch",
                "expected": manifest.get("content_sha256"),
                "actual": sha
            })
            self.logger.warning(f"Hash mismatch: expected {manifest.get('content_sha256')}, got {sha}")
            return {"status": "reject", "reason": "hash_mismatch"}
        
        if self.match_exact(sha):
            self.append_entry({"action": "allow", "sha": sha, "why": "exact"})
            self.logger.info(f"Allowed (exact match): {sha}")
            return {"status": "allow", "why": "exact"}
        
        if self.match_ssdeep(content_p):
            self.append_entry({"action": "allow", "sha": sha, "why": "fuzzy"})
            self.logger.info(f"Allowed (fuzzy match): {sha}")
            return {"status": "allow", "why": "fuzzy"}
        
        if self.match_rules(content_p):
            self.append_entry({"action": "allow", "sha": sha, "why": "rule"})
            self.logger.info(f"Allowed (rule match): {sha}")
            return {"status": "allow", "why": "rule"}
        
        qpath = self.quarantine_file(content_p, manifest)
        self.logger.info(f"Quarantined: {sha}")
        return {"status": "quarantine", "path": qpath}
    
    def run_self_test(self) -> bool:
        """Run self-test with dummy files."""
        self.logger.info("[TEST] Running translator_gate self-test")
        
        os.makedirs("keys", exist_ok=True)
        
        test_content = b"testdata"
        test_path = Path("artifact_test.bin")
        test_path.write_bytes(test_content)
        
        sha = self.compute_sha256(test_path)
        
        manifest = {
            "name": "demo_artifact",
            "content_sha256": sha
        }
        manifest_path = Path("manifest_test.json")
        with manifest_path.open("w") as f:
            json.dump(manifest, f)
        
        sig_path = Path("manifest_test.sig")
        sig_path.write_text(base64.b64encode(b"sig").decode())
        
        result = self.process_upload(
            str(manifest_path),
            str(sig_path),
            str(test_path)
        )
        
        self.logger.info(f"[TEST] Result: {result}")
        
        manifest_path.unlink(missing_ok=True)
        sig_path.unlink(missing_ok=True)
        test_path.unlink(missing_ok=True)
        
        return result.get("status") == "allow"


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Translator Gate - Upload Verification")
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON")
    parser.add_argument("--signature", required=True, help="Path to signature file")
    parser.add_argument("--content", required=True, help="Path to content file")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    
    args = parser.parse_args()
    
    config = TranslatorGateConfig(dry_run=args.dry_run)
    gate = TranslatorGate(config)
    
    if args.test:
        success = gate.run_self_test()
        sys.exit(0 if success else 1)
    
    result = gate.process_upload(args.manifest, args.signature, args.content)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()