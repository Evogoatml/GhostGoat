"""Brain agents module"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from memory.vault import Memory
except ImportError:
    Memory = None
__all__ = ['Memory']
