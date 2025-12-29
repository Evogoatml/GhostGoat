import os, json, time

PATH = "adap/data/user_behavior.json"

def record(command, result):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    entry = {
        "ts": int(time.time()),
        "command": command,
        "result": result
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

def suggest():
    from collections import Counter
    cmds = [e["command"] for e in load()]
    if not cmds:
        return None
    return Counter(cmds).most_common(1)[0][0]
