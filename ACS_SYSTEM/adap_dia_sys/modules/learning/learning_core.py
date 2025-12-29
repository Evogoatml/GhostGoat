# modules/learning/learning_core.py
import json, os, time, statistics

DATA_PATH = os.path.expanduser("~/adaptive_vault/data/task_memory.json")

def record(task, result, metrics=None):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    entry = {
        "task": task,
        "time": time.time(),
        "result": result,
        "metrics": metrics or {}
    }
    memory = []
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            memory = json.load(f)
    memory.append(entry)
    with open(DATA_PATH, "w") as f:
        json.dump(memory[-250:], f, indent=2)
    print(f"[LEARN] Recorded {task} result={result}")

def summarize_task(task):
    """Analyze historical results for a given task"""
    if not os.path.exists(DATA_PATH):
        return None
    with open(DATA_PATH, "r") as f:
        memory = json.load(f)
    entries = [m for m in memory if m["task"] == task]
    if not entries:
        return None
    durations = [m["metrics"].get("duration", 0) for m in entries if "metrics" in m]
    avg_time = statistics.mean(durations) if durations else 0
    success_rate = sum(1 for m in entries if m["result"] == "success") / len(entries)
    return {"runs": len(entries), "avg_time": avg_time, "success_rate": round(success_rate, 2)}
