#!/usr/bin/env python3
"""
CLI sniffer - polls GhostGoat's AgentBus for messages.
Run this while telegram_bot.py is running to see messages.
"""
import sys
import os
import json
import time

sys.path.insert(0, "/home/popic/GhostGoat")
os.chdir("/home/popic/GhostGoat")

print("🔌 GhostGoat Message Sniffer")
print("=" * 50)
print("Waiting for messages... (Ctrl+C to stop)\n")

last_count = 0

try:
    while True:
        try:
            from core.bus.agent_bus import bus
            msgs = bus.recent(20)
            
            # Show new messages
            if len(msgs) > last_count:
                new_msgs = msgs[last_count:]
                for m in new_msgs:
                    topic = m.get("topic", "?")
                    payload = m.get("payload", {})
                    if isinstance(payload, dict):
                        payload = json.dumps(payload, indent=2)[:200]
                    print(f"📨 [{topic}] {payload}")
                    print("-" * 40)
                last_count = len(msgs)
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n\n🛑 Stopped.")