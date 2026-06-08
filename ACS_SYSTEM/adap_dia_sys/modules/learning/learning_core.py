import json
import os
from datetime import datetime
from typing import Dict, List, Optional

FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "task_memory.json")


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


def record(task: str, result: str, metrics: Optional[Dict] = None):
    entry = {
        "task": task,
        "result": result,
        "timestamp": datetime.now().timestamp(),
        "metrics": metrics or {},
    }
    data = load()
    data.append(entry)
    _save(data)


def summarize(task: str) -> str:
    records = [e for e in load() if e["task"] == task]
    if not records:
        return f"No records for: {task}"
    success = sum(1 for e in records if e["result"] == "success")
    total = len(records)
    return f"{task}: {success}/{total}"