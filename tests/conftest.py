"""Ensure the project root is on sys.path for test imports."""

import sys
import os

# Make the project root the first entry on the path so project imports resolve.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_BYTE_ROOT = os.path.join(ROOT, "agent_byte-master")
for path in (ROOT, AGENT_BYTE_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)
