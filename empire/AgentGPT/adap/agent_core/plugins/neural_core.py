import os, json

PATH = "adap/data/brain_core.json"

STATE = {'stability': 0.5, 'efficiency': 0.5, 'awareness': 0.5}

def update(result):
    global STATE
    if result == "success":
        STATE['stability'] = min(1.0, STATE['stability'] + 0.01)
        STATE['efficiency'] = min(1.0, STATE['efficiency'] + 0.01)
    else:
        STATE['stability'] = max(0.0, STATE['stability'] - 0.01)
        STATE['efficiency'] = max(0.0, STATE['efficiency'] - 0.01)
    save()

def save():
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(STATE, f, indent=2)

def introspect():
    return STATE
