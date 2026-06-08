"""
Root conftest.py — ensures the project root is on sys.path so that all
package imports (config, core, frameworks, …) resolve correctly without
any manual sys.path hacking inside individual test files.
"""

import sys
import os

# Make the project root the first entry on the path so that
# `from config.unified_config import …` etc. always resolves.
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
