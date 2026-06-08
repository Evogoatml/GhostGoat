
"""
ACS adap_pipeline → GhostGoat Tool Registry Bridge.

Drops any .py module into ACS_SYSTEM/adap_pipeline/modules/
and it becomes a callable GhostGoat tool automatically.
"""

import os
import sys
import logging
import importlib.util
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# GhostGoat tool registry
try:
    from tools.registry import registry as _registry
    _HAS_REGISTRY = True
except Exception:
    _HAS_REGISTRY = False
    _registry = None

# adap_pipeline core
try:
    from ACS_SYSTEM.adap_pipeline.core_controller import ModuleWrapper
    _HAS_ADAP = True
except Exception:
    _HAS_ADAP = False
    ModuleWrapper = None


class AdapPipelineBridge:
    """
    Auto-discovers adap_pipeline modules and registers them
    as GhostGoat tools via the tool registry.
    """

    MODULE_PATH = "ACS_SYSTEM/adap_pipeline/modules"

    def __init__(self):
        self.modules: Dict[str, Any] = {}
        self.tools_registered = 0

    def discover(self) -> Dict[str, Any]:
        """Find all modules in the adap_pipeline modules directory."""
        discovered = {}
        if not os.path.isdir(self.MODULE_PATH):
            logger.warning("adap_pipeline modules dir not found: %s", self.MODULE_PATH)
            return discovered

        for fname in os.listdir(self.MODULE_PATH):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue

            mod_name = fname[:-3]
            mod_path = os.path.join(self.MODULE_PATH, fname)

            try:
                spec = importlib.util.spec_from_file_location(mod_name, mod_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                discovered[mod_name] = mod
                logger.info("Discovered adap module: %s", mod_name)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", mod_name, exc)

        self.modules = discovered
        return discovered

    def _wrap_module_function(self, mod: Any, func_name: str) -> Callable:
        """Wrap a module function as a GhostGoat tool."""
        def tool_wrapper(**kwargs):
            try:
                if hasattr(mod, func_name):
                    return getattr(mod, func_name)(**kwargs)
                elif hasattr(mod, "main"):
                    return mod.main(**kwargs)
                elif hasattr(mod, "run"):
                    return mod.run(**kwargs)
                else:
                    return {"error": f"No callable function in {mod.__name__}"}
            except Exception as exc:
                return {"error": str(exc)}

        tool_wrapper.__name__ = f"adap_{func_name}"
        return tool_wrapper

    def register_all(self) -> int:
        """Register all discovered modules as GhostGoat tools."""
        if not _HAS_REGISTRY or _registry is None:
            logger.warning("GhostGoat tool registry not available")
            return 0

        count = 0
        for mod_name, mod in self.modules.items():
            try:
                # Register main entry points as tools
                for func_name in ["main", "run", "execute"]:
                    if hasattr(mod, func_name):
                        tool_name = f"adap_{mod_name}_{func_name}"
                        wrapper = self._wrap_module_function(mod, func_name)
                        _registry.register(tool_name, wrapper)
                        count += 1
                        logger.info("Registered tool: %s", tool_name)

                # Also try ModuleWrapper if available
                if _HAS_ADAP and ModuleWrapper:
                    wrapper = ModuleWrapper(mod_name, mod)
                    tool_name = f"adap_{mod_name}"
                    _registry.register(tool_name, wrapper.call)
                    count += 1

            except Exception as exc:
                logger.warning("Failed to register %s: %s", mod_name, exc)

        self.tools_registered = count
        return count

    def get_module_list(self) -> list:
        return list(self.modules.keys())


# Global bridge
adap_bridge = AdapPipelineBridge()
