"""
Plugin discovery and loading.

Relocated from empire/AgentGPT's PluginManager + command_core.
Scans a directory for Python modules and registers tools/commands
found inside them.

Usage:
    loader = PluginLoader("/path/to/plugins")
    toolkit = loader.discover()
    # toolkit now contains all BaseTool subclasses found in the directory
"""

import importlib
import importlib.util
import inspect
import logging
import os
from typing import Dict, List, Optional

from frameworks.agents.tools import BaseTool, Toolkit

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discover and load BaseTool plugins from a directory.

    Scans .py files in the given directory, imports them, and collects
    any BaseTool subclass instances or classes.
    """

    def __init__(self, plugins_dir: str, toolkit_name: str = "plugins"):
        self._dir = plugins_dir
        self._toolkit_name = toolkit_name

    def discover(self) -> Toolkit:
        """Scan the plugins directory and return a Toolkit of discovered tools."""
        toolkit = Toolkit(name=self._toolkit_name, description=f"Plugins from {self._dir}")

        if not os.path.isdir(self._dir):
            logger.warning("Plugin directory does not exist: %s", self._dir)
            return toolkit

        for fname in sorted(os.listdir(self._dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue

            module_name = fname[:-3]
            filepath = os.path.join(self._dir, fname)

            try:
                mod = self._load_module(module_name, filepath)
                tools = self._extract_tools(mod)
                for tool in tools:
                    toolkit.add(tool)
                    logger.debug("Loaded plugin tool: %s from %s", tool.name, fname)
            except Exception as e:
                logger.warning("Failed to load plugin %s: %s", fname, e)

        logger.info("Discovered %d plugin tools from %s",
                     len(toolkit.get_tools()), self._dir)
        return toolkit

    def _load_module(self, name: str, filepath: str):
        """Import a Python module from a file path."""
        spec = importlib.util.spec_from_file_location(f"plugins.{name}", filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _extract_tools(self, module) -> List[BaseTool]:
        """Find BaseTool subclasses in a module and instantiate them."""
        tools = []
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                try:
                    instance = obj()
                    if instance.name:
                        tools.append(instance)
                except Exception as e:
                    logger.debug("Could not instantiate %s: %s", name, e)
        return tools
