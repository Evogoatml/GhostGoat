"""
Agent framework registry.

Auto-discovers which agent backends are installed and provides a single
entry-point to get a ready-to-use adapter.

    from frameworks.agents.registry import get_framework, list_frameworks

    fw = get_framework()          # best available
    fw = get_framework("crewai")  # explicit pick
"""

import logging
from typing import Dict, Optional

from frameworks.agents.base import AgentFramework

logger = logging.getLogger(__name__)

# Registered adapter classes (import path -> class).
# The dict is ordered by preference — first available wins in get_framework().
_BACKENDS: Dict[str, type] = {}


def _discover():
    """Populate _BACKENDS with all known adapter classes."""
    if _BACKENDS:
        return

    from frameworks.agents.crewai_adapter import CrewAIFramework
    from frameworks.agents.swarms_adapter import SwarmsFramework
    from frameworks.agents.langgraph_adapter import LangGraphFramework

    _BACKENDS["crewai"] = CrewAIFramework
    _BACKENDS["swarms"] = SwarmsFramework
    _BACKENDS["langgraph"] = LangGraphFramework


def list_frameworks() -> Dict[str, bool]:
    """Return dict of framework name -> installed."""
    _discover()
    result = {}
    for name, cls in _BACKENDS.items():
        try:
            result[name] = cls().available()
        except Exception:
            result[name] = False
    return result


def get_framework(name: Optional[str] = None, **kwargs) -> AgentFramework:
    """Get an agent framework adapter.

    Args:
        name: Explicit backend name ("crewai" or "swarms").
              If None, returns the first available.
        **kwargs: Passed to the adapter constructor.

    Returns:
        An AgentFramework instance.

    Raises:
        RuntimeError: If the requested (or any) backend is unavailable.
    """
    _discover()

    if name:
        cls = _BACKENDS.get(name)
        if cls is None:
            raise ValueError(f"Unknown agent framework: {name!r}. "
                             f"Known: {list(_BACKENDS)}")
        fw = cls(**kwargs)
        if not fw.available():
            raise RuntimeError(
                f"Agent framework {name!r} is not installed. "
                f"Install it with: pip install {name}"
            )
        return fw

    # Auto-select first available
    for bname, cls in _BACKENDS.items():
        try:
            fw = cls(**kwargs)
            if fw.available():
                logger.info("Auto-selected agent framework: %s", bname)
                return fw
        except Exception:
            continue

    raise RuntimeError(
        "No agent framework installed. Install one with:\n"
        "  pip install crewai      # or\n"
        "  pip install swarms"
    )
