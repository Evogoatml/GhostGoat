import os, json, time

PATH = "adap/data/task_memory.json"

def record(task, result, metrics=None):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    entry = {
        "ts": time.time(),
        "task": task,
        "result": result,
        "metrics": metrics or {}
    }
    data = []
    if os.path.exists(PATH):
        with open(PATH) as f:
            data = json.load(f)
    data.append(entry)
    with open(PATH, "w") as f:
        json.dump(data, f, indent=2)

def load():
    if not os.path.exists(PATH):
        return []
    with open(PATH) as f:
        return json.load(f)

def summarize(task):
    events = [e for e in load() if e.get("task") == task]
    if not events:
        return {"task": task, "count": 0, "success": 0, "fail": 0}
    succ = sum(1 for e in events if e.get("result") == "success")
    fail = sum(1 for e in events if e.get("result") != "success")
    return {"task": task, "count": len(events), "success": succ, "fail": fail}
