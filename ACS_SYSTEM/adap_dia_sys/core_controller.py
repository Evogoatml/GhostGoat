#!/usr/bin/env python3
"""
Adaptive Vault Core Controller.
Dynamically loads and orchestrates governance, efficiency, and diagnostics modules.
"""
from __future__ import annotations

import importlib
import traceback
import time
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class ControllerConfig:
    """Configuration for the core controller."""
    cycle_interval: int = 10
    modules_dir: str = "modules"
    dry_run: bool = False
    auto_fix: bool = True
    log_level: str = "INFO"


class ModuleWrapper:
    """Dynamic module loader with error handling."""
    
    def __init__(self, name: str, config: Optional[ControllerConfig] = None):
        self.name = name
        self.config = config or ControllerConfig()
        self.module = None
        self.loaded = False
        self._logger = logging.getLogger(f"module.{name}")
    
    def load(self) -> bool:
        """Load the module dynamically."""
        try:
            self.module = importlib.import_module(f"{self.config.modules_dir}.{self.name}")
            self.loaded = True
            self._logger.info(f"[LOAD OK] {self.name}")
            return True
        except ImportError as e:
            self._logger.warning(f"[LOAD FAIL] {self.name}: {e}")
            self.module = None
            self.loaded = False
            return False
        except Exception as e:
            self._logger.error(f"[LOAD ERROR] {self.name}: {e}")
            self.module = None
            self.loaded = False
            return False
    
    def call(self, func_name: str, *args: Any, **kwargs: Any) -> Any:
        """Call a function in the loaded module."""
        if not self.module or not self.loaded:
            return None
        
        try:
            func = getattr(self.module, func_name)
            return func(*args, **kwargs)
        except AttributeError:
            self._logger.warning(f"[CALL] {self.name}.{func_name} not found")
            return None
        except Exception:
            self._logger.error(f"[CALL ERROR] {self.name}.{func_name}")
            traceback.print_exc()
            return None
    
    def is_loaded(self) -> bool:
        """Check if module loaded successfully."""
        return self.loaded and self.module is not None


class AdaptiveVault:
    """Adaptive vault that loads and orchestrates modules."""
    
    DEFAULT_MODULES = {
        "governance.decision_governor": "governance.decision_governor",
        "efficiency_engine": "efficiency_engine",
        "diagnostics.self_check": "diagnostics.self_check",
    }
    
    def __init__(self, config: Optional[ControllerConfig] = None):
        self.config = config or ControllerConfig()
        self._setup_logging()
        self.modules: dict[str, ModuleWrapper] = {}
        self._running = False
        self._setup_signal_handlers()
        self._initialize_modules()
    
    def _setup_logging(self) -> None:
        self.logger = logging.getLogger("adaptive_vault")
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(getattr(logging, self.config.log_level))
    
    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        self.logger.info(f"Received signal {signum}, shutting down...")
        self._running = False
    
    def _initialize_modules(self) -> None:
        """Initialize module wrappers."""
        for name in self.DEFAULT_MODULES.values():
            self.modules[name] = ModuleWrapper(name, self.config)
    
    def register_module(self, name: str) -> None:
        """Register an additional module."""
        if name not in self.modules:
            self.modules[name] = ModuleWrapper(name, self.config)
            self.logger.info(f"Registered module: {name}")
    
    def unregister_module(self, name: str) -> None:
        """Unregister a module."""
        if name in self.modules:
            del self.modules[name]
            self.logger.info(f"Unregistered module: {name}")
    
    def startup(self) -> bool:
        """Load all modules and start the vault."""
        self.logger.info("\n🧠 Booting Adaptive Vault...")
        
        success_count = 0
        for name, mod in self.modules.items():
            if mod.load():
                success_count += 1
        
        self.logger.info(f"[CORE] Loaded {success_count}/{len(self.modules)} modules")
        
        if success_count == 0:
            self.logger.error("[CORE] No modules loaded!")
            return False
        
        self.logger.info("[CORE] Initialization complete.\n")
        return True
    
    def shutdown(self) -> None:
        """Graceful shutdown."""
        self.logger.info("[CORE] Shutting down...")
        self._running = False
        self.logger.info("[CORE] Shutdown complete.")
    
    def run_cycle(self) -> dict:
        """Run one system cycle."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "modules": {},
            "success": True,
        }
        
        diag = self.modules.get("diagnostics.self_check")
        if diag and diag.is_loaded():
            try:
                diag_result = diag.call("run_all", auto_fix=self.config.auto_fix)
                results["modules"]["diagnostics"] = diag_result
                if diag_result:
                    self.logger.debug(f"Diagnostics: {json.dumps(diag_result)[:200]}")
            except Exception as e:
                self.logger.error(f"Diagnostics error: {e}")
                results["modules"]["diagnostics"] = {"error": str(e)}
                results["success"] = False
        
        return results
    
    def main_loop(self) -> None:
        """Main operational loop."""
        self._running = True
        self.logger.info(f"[CORE] Starting main loop (interval: {self.config.cycle_interval}s)")
        
        while self._running:
            ts = datetime.now().strftime("%H:%M:%S")
            self.logger.info(f"[{ts}] Running system cycle...")
            
            results = self.run_cycle()
            
            if self.config.dry_run:
                self.logger.info(f"[DRY-RUN] Cycle results: {json.dumps(results, indent=2)}")
            
            try:
                time.sleep(self.config.cycle_interval)
            except KeyboardInterrupt:
                break
        
        self.shutdown()


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adaptive Vault Core Controller")
    parser.add_argument("--cycle-interval", type=int, default=10, help="Cycle interval in seconds")
    parser.add_argument("--modules-dir", default="modules", help="Modules directory")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--auto-fix", type=bool, default=True, help="Auto-fix enabled")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    config = ControllerConfig(
        cycle_interval=args.cycle_interval,
        modules_dir=args.modules_dir,
        dry_run=args.dry_run,
        auto_fix=args.auto_fix,
        log_level=args.log_level,
    )
    
    vault = AdaptiveVault(config)
    
    if not vault.startup():
        sys.exit(1)
    
    vault.main_loop()


if __name__ == "__main__":
    main()