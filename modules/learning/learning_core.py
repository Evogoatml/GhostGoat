
import json, os, time
FILE = 'adap/data/task_memory.json'

def record(task, result, metrics=None):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    data = load()
    entry = {
        "task": task,
        "result": result,
        "metrics": metrics or {},
        "timestamp": time.time()
    }
    data.append(entry)
    with open(FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load():
    if os.path.exists(FILE):
        with open(FILE) as f:
            return json.load(f)
    return []

def summarize(task):
    data = [d for d in load() if d['task'] == task]
    if not data:
        return f'No records for {task}'
    success = sum(1 for d in data if d['result']=='success')
    return f'{task}: {success}/{len(data)} successes'
