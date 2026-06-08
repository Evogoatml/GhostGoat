#!/usr/bin/env python3
"""
Adaptive Vault Main Entry Point.
Scans and loads modules, then starts the adaptive vault core.
"""
from __future__ import annotations

import os
import sys
import time
import importlib
import logging
from pathlib import Path


class VaultConfig:
    """Configuration for the vault."""
    base_dir: str = ""
    core_dir: str = ""
    module_dir: str = ""
    log_level: str = "INFO"


def load_config() -> VaultConfig:
    """Load configuration from environment or defaults."""
    config = VaultConfig()
    config.base_dir = os.environ.get("VAULT_BASE_DIR", os.path.dirname(__file__))
    config.core_dir = os.path.join(config.base_dir, "core")
    config.module_dir = os.path.join(config.base_dir, "modules")
    config.log_level = os.environ.get("VAULT_LOG_LEVEL", "INFO")
    return config


def setup_logging(config: VaultConfig) -> logging.Logger:
    """Setup logging."""
    logger = logging.getLogger("adaptive_vault")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.log_level))
    return logger


def load_modules(mod_path: str, logger: logging.Logger) -> list[str]:
    """Dynamically import all Python modules in the /modules folder."""
    logger.info(f"[SYSTEM] Scanning {mod_path} for modules...")
    
    path = Path(mod_path)
    if not path.exists():
        logger.warning(f"[SYSTEM] Module directory not found: {mod_path}")
        return []
    
    loaded = []
    for file in path.iterdir():
        if not file.suffix == ".py" or file.stem.startswith("_"):
            continue
        
        mod_name = file.stem
        try:
            mod = importlib.import_module(mod_name)
            loaded.append(mod_name)
            logger.debug(f"[LOAD] {mod_name}")
        except Exception as e:
            logger.warning(f"[WARN] Failed to load module '{mod_name}': {e}")
    
    if loaded:
        logger.info(f"[MODULES ACTIVE] {', '.join(loaded)}")
    else:
        logger.info("[MODULES] No modules found.")
    
    return loaded


def start_vault(logger: logging.Logger, config: VaultConfig) -> None:
    """Import and launch the adaptive vault main loop."""
    try:
        from adaptive_vault import main as vault_main
    except ImportError as e:
        logger.error(f"[ERROR] Core vault could not be imported: {e}")
        return
    
    logger.info("[SYSTEM] Adaptive Vault core initializing...")
    vault_main()


def main():
    """Main execution."""
    config = load_config()
    logger = setup_logging(config)
    
    print("=" * 65)
    print("🧠 Adaptive Vault — Modular Intelligence Framework")
    print("=" * 65)
    logger.info(f"[BOOT] Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    modules_loaded = load_modules(config.module_dir, logger)
    logger.info("[BOOT] Loading core system...")
    
    start_vault(logger, config)
    
    return modules_loaded


if __name__ == "__main__":
    main()