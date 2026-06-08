#!/usr/bin/env python3
"""
Adaptive Vault - Live Adaptive Console System

Production-grade rewrite with:
- Proper package imports
- Type hints throughout
- Structured logging
- Atomic append writes
- Configurable polling
- Graceful error recovery
"""

import sys
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from threading import Event

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("audit.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class VaultConfig:
    """Configuration for adaptive vault."""
    poll_interval: float = 5.0
    diag_interval: float = 600.0
    audit_path: str = "audit.log"  # Relative by default
    manifest_pattern: str = "manifest.json"
    sig_pattern: str = "manifest.sig"
    artifact_pattern: str = "artifact.bin"
    env_file: str = ".env"


class AdaptiveVault:
    """Production adaptive vault with proper resource management."""
    
    def __init__(self, config: Optional[VaultConfig] = None, dry_run: bool = False):
        self.config = config or VaultConfig()
        self.dry_run = dry_run
        self.running = Event()
        self._last_diag = 0.0  # 0 = run immediately on first cycle
        
        # Lazy-loaded components
        self._core = None
        self._translator = None
        self._policy = None
        self._crypto = None
        self._monitor = None
        
        logger.info(f"AdaptiveVault initialized (dry_run={dry_run})")

    @property
    def core(self):
        if self._core is None:
            try:
                from modules.learning.neural_core import NeuralCore
                self._core = NeuralCore()
            except ImportError:
                self._core = None
        return self._core

    @property
    def translator(self):
        if self._translator is None:
            from translator_gate import process_upload
            self._translator = process_upload
        return self._translator

    @property
    def policy(self):
        if self._policy is None:
            from policy import choose_cipher
            self._policy = choose_cipher
        return self._policy

    @property
    def crypto(self):
        if self._crypto is None:
            from crypto import sign_log  # Only load what we use
            self._crypto = sign_log
        return self._crypto

    @property
    def monitor(self):
        if self._monitor is None:
            from monitor import get_resource_state
            self._monitor = get_resource_state
        return self._monitor

    def load_env(self, base_dir: Path) -> Dict[str, str]:
        """Load environment variables safely."""
        env_path = base_dir / self.config.env_file
        env = {}
        
        if not env_path.exists():
            logger.warning(f".env not found at {env_path}")
            return env
            
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line:
                    key, _, value = line.partition("=")
                    env[key.strip()] = value.strip()
                    
        logger.info(f"Loaded mission: {env.get('MISSION', 'unknown')}")
        return env

    def check_input_files(self, base_dir: Path) -> Optional[Dict[str, Path]]:
        """Check for required input files efficiently."""
        required = {
            "manifest": base_dir / self.config.manifest_pattern,
            "sig": base_dir / self.config.sig_pattern,
            "artifact": base_dir / self.config.artifact_pattern,
        }
        
        missing = [name for name, path in required.items() if not path.exists()]
        
        if missing:
            logger.debug(f"Waiting for files: {missing}")
            return None
            
        return {name: path for name, path in required.items()}

    def write_audit_entry(self, base_dir: Path, entry: Dict[str, Any]) -> None:
        """Append to audit log atomically."""
        if self.dry_run:
            logger.debug(f"DRY RUN: would write {entry}")
            return
        
        # Handle absolute vs relative audit_path
        audit_path = Path(self.config.audit_path)
        if audit_path.is_absolute():
            full_path = audit_path
        else:
            full_path = base_dir / audit_path
            
        entry_json = json.dumps(entry, sort_keys=True)
        
        # Atomic append: lock + write + unlock pattern
        # For simplicity, use single-file append (os level is atomic for <4KB)
        with open(full_path, "a", encoding="utf-8") as f:
            f.write(entry_json + "\n")

    def maybe_run_diagnostics(self) -> None:
        """Periodic diagnostics with proper interval."""
        now = time.time()
        if now - self._last_diag > self.config.diag_interval:
            try:
                from modules.performance_profiler import run_all
                run_all(auto_fix=True, auto_install=False)
                self._last_diag = now
                logger.info("Diagnostics completed")
            except ImportError:
                logger.debug("Diagnostics module not available")

    def process_cycle(self, base_dir: Path, mission: Dict[str, str]) -> bool:
        """Single processing cycle. Returns True if successful."""
        files = self.check_input_files(base_dir)
        if not files:
            self._log_state("waiting", 0.0, "-", "No input files")
            return False

        self.core.record_experience("core_loop", "success")

        # Run translator gate
        try:
            result = self.translator(
                str(files["manifest"]),
                str(files["sig"]),
                str(files["artifact"])
            )
            gate_status = result.get("status", "error")
        except Exception as e:
            logger.exception("Translator gate failed")
            self.core.record_experience("translator_gate", "failure")
            self._log_state("error", 0.0, "-", f"Translation error: {e}")
            return False

        if gate_status != "allow":
            self.core.record_experience("translator_gate", "failure")
            self._log_state(gate_status, 0.0, "-", "Quarantined/rejected")
            return False

        self.core.record_experience("translator_gate", "success")

        try:
            metrics = self.monitor()
            cipher = self.policy(metrics, mission)
            cpu = metrics.get("cpu", 0.0)
        except Exception as e:
            logger.warning(f"Metric gathering failed: {e}")
            cpu = 0.0
            cipher = "aesgcm"

        # Record performance - latency as cpu percentage (0.0-1.0 normalized)
        latency = cpu / 100.0 if cpu > 0 else 0.01
        self.core.record_experience("efficiency_engine", "success", latency=latency)

        # Build and sign audit entry
        entry = {
            "ts": time.time(),
            "cpu": cpu,
            "cipher": cipher,
            "gate_status": gate_status
        }
        
        sign_log = self.crypto
        signed_entry = sign_log(entry)

        self.write_audit_entry(base_dir, signed_entry)

        self._log_state(gate_status, cpu, cipher, "System active")
        return True

    def _log_state(self, gate_status: str, cpu: float, cipher: str, message: str) -> None:
        """Formatted console output."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{ts}] GATE: {gate_status:<10} | CPU: {cpu:>5.1f}% | Cipher: {cipher:<8} | {message}"
        print(msg)
        logger.debug(msg)

    def run(self, base_dir: Optional[Path] = None) -> None:
        """Main running loop with proper shutdown."""
        base_dir = base_dir or Path.cwd()
        
        logger.info("Starting Adaptive Vault...")
        mission = self.load_env(base_dir)
        print(f"[INIT] Mission loaded: {mission.get('MISSION', 'unknown')}")

        self.running.set()
        
        try:
            while self.running.is_set():
                try:
                    self.process_cycle(base_dir, mission)
                    self.maybe_run_diagnostics()
                    self.running.wait(timeout=self.config.poll_interval)
                    
                except KeyboardInterrupt:
                    logger.info("Interrupt received")
                    break
                except Exception as e:
                    logger.exception(f"Unexpected error: {e}")
                    self.core.record_experience("core_loop", "failure")
                    self._log_state("error", 0.0, "-", f"CYCLE ERROR: {e}")
                    time.sleep(1)
                    
        finally:
            self.shutdown(base_dir)

    def shutdown(self, base_dir: Path) -> None:
        """Graceful shutdown with introspection."""
        print("\n[SHUTDOWN] Initiating graceful shutdown...")
        
        if self._core:
            try:
                self._core.introspect()
            except Exception as e:
                logger.warning(f"Introspection failed: {e}")
                
        logger.info("Adaptive Vault shut down complete")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adaptive Vault System")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--poll-interval", type=float, default=5.0,
                       help="Poll interval in seconds")
    parser.add_argument("--diag-interval", type=float, default=600.0,
                       help="Diagnostic interval in seconds")
    args = parser.parse_args()

    config = VaultConfig(
        poll_interval=args.poll_interval,
        diag_interval=args.diag_interval,
    )
    
    vault = AdaptiveVault(config=config, dry_run=args.dry_run)
    vault.run()


if __name__ == "__main__":
    main()
