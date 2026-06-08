#!/usr/bin/env python3
"""Patch telegram_bot.py to add vendor path for Agent Byte"""
import os

filepath = os.path.join(os.path.dirname(__file__), '..', 'integrations', 'telegram_bot.py')

with open(filepath, 'r') as f:
    content = f.read()

if '_VENDOR' not in content:
    # Add vendor path after sys.path.insert(0, _ROOT)
    old = "sys.path.insert(0, _ROOT)"
    new = """sys.path.insert(0, _ROOT)

# Add vendor folder for Agent Byte
_VENDOR = os.path.join(_ROOT, "vendor", "agent_byte-master")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)"""
    content = content.replace(old, new)
    
    with open(filepath, 'w') as f:
        f.write(content)
    print("Patched telegram_bot.py - vendor path added")
else:
    print("Already patched")