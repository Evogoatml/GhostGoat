"""
View adap agent logs
@jarviscmd: Display action logs and memory.
"""

import os, json

def run():
    path = "../data/memory.db"
    if os.path.exists(path):
        with open(path) as f:
            mem = json.load(f)
        logs = mem.get("logs", [])
        for entry in logs:
            print(entry)
    else:
        print("No logs found.")
