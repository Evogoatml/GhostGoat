"""Top‑level package for GhostGoat.

We expose the ``system`` singleton so callers can simply do:
    ``from brain import system``

The legacy ``agent_byte-master`` codebase is no longer needed for normal
operation, so we do **not** modify ``sys.path`` here.  If a future component
requires legacy modules they can add the path explicitly.
"""

# Export the system façade defined in ``brain/system.py``
from .system import system  # noqa: F401
