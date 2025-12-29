#!/usr/bin/env python3
# modules/learning/user_behavior.py
import os, json, time

DATA_FILE = os.path.expanduser("~/adaptive_vault/data/user_behavior.json")

def _load():
    """Internal: load existing behavior data"""
    if not os.path.exists(DATA_FILE):
        return {"commands": []}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return {"commands": []}

def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def record(cmd_name, result="success", context=None):
    """Record a user action"""
    data = _load()
    entry = {
        "timestamp": time.time(),
        "cmd": cmd_name,
        "result": result,
        "context": context or {}
    }
    data["commands"].append(entry)
    # keep last 500 actions
    data["commands"] = data["commands"][-500:]
    _save(data)
    print(f"[LEARN] Behavior recorded: {cmd_name} ({result})")

def summarize(top_n=5):
    """Summarize user command patterns"""
    data = _load()
    cmds = [e["cmd"] for e in data["commands"]]
    if not cmds:
        return {}
    summary = {}
    for c in cmds:
        summary[c] = summary.get(c, 0) + 1
    top = sorted(summary.items(), key=lambda x: x[1], reverse=True)[:top_n]
    print("\n🧠 User Behavior Summary (Top Commands):")
    for cmd, count in top:
        print(f"   {cmd}: used {count} times")
    print()
    return summary

def suggest_next():
    """Suggest next logical command based on usage patterns"""
    summary = summarize()
    if not summary:
        print("No data yet — start running diagnostics to build patterns.")
        return None
    most_common = max(summary, key=summary.get)
    suggestion_map = {
        "efficiency_optimization": "performance_metrics",
        "external_intelligence_sync": "policy_validation",
        "system_health_check": "audit_integrity_check"
    }
    suggestion = suggestion_map.get(most_common, None)
    if suggestion:
        print(f"💡 Suggestion: After '{most_common}', try '{suggestion}' next.")
    else:
        print(f"💡 Suggestion: Re-run '{most_common}' to confirm consistency.")
    return suggestion
