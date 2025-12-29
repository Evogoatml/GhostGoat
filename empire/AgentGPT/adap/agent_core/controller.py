import re
from typing import TYPE_CHECKING, Optional

# --- Auto initialize Plugin Intelligence Loader ---
try:
    from adap.agent_core import plugin_intel
    print("[ADAP] scanning for new plugins...")
    plugin_intel.build_registry()
    print("[ADAP] plugin registry refreshed")
except Exception as e:
    print(f"[ADAP] plugin init failed: {e}")
# --------------------------------------------------

if TYPE_CHECKING:
    from .agent import AdapAgent  # for hints only

_GH_PATTERN = r'(https?://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)'

def detect_and_clone_github_url(user_input: str) -> Optional[str]:
    """Return repo URL if present; cloning can be added later."""
    m = re.search(_GH_PATTERN, user_input)
    return m.group(1) if m else None
