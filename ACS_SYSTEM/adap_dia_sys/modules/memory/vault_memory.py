import json, time
from pathlib import Path

MEMORY_PATH = Path.home() / "adaptive_vault" / "data" / "vault_memory.json"

def load_memory():
    if MEMORY_PATH.exists():
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"history": []}

def save_memory(data):
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def record_snapshot(report):
    data = load_memory()
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report["ts"]))
    summary = {
        "timestamp": ts,
        "missing": len(report.get("missing_required_files", [])),
        "actions": [list(a.keys())[0] for a in report.get("actions", [])],
        "stable": not bool(report.get("missing_required_files")),
    }
    data["history"].append(summary)
    # keep only the last 50 runs to prevent bloat
    data["history"] = data["history"][-50:]
    save_memory(data)
    return summary

def summarize_trends():
    data = load_memory()
    hist = data.get("history", [])
    total = len(hist)
    if total == 0:
        return "🪶 No memory yet. Run diagnostics to build history."
    stable = sum(1 for h in hist if h["stable"])
    ratio = round((stable / total) * 100, 1)
    last = hist[-1]
    msg = [
        f"🧭  Total runs recorded: {total}",
        f"📈  Stability ratio: {ratio}%",
        f"🕓  Last run: {last['timestamp']}",
        f"🔧  Last actions: {', '.join(last['actions']) or 'None'}"
    ]
    return "\n".join(msg)
