import json
import os
from collections import Counter
from datetime import datetime
from typing import Dict, List

FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "user_behavior.json")


def load() -> List[Dict]:
    if not os.path.exists(FILE):
        return []
    try:
        return json.loads(open(FILE).read())
    except (json.JSONDecodeError, IOError):
        return []


def _save(data: List[Dict]):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    open(FILE, "w").write(json.dumps(data, indent=2))


def record(command: str, result: str):
    entry = {"command": command, "result": result, "time": datetime.now().timestamp()}
    data = load()
    data.append(entry)
    _save(data)


def suggest() -> str:
    records = load()
    if not records:
        return "No suggestions available."
    top = Counter(e["command"] for e in records).most_common(3)
    return ", ".join(c for c, _ in top)