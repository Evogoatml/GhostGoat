# modules/recommendation_engine.py
"""
Recommendation Engine
Analyzes efficiency reports and performance patterns to suggest improvements.
Lightweight, capped logs, no auto-patching.
"""

import os, json, time

SUMMARY_FILE = "audit/efficiency_summary.json"
REPORT_FILE  = "audit/recommendations.json"
MAX_REPORTS  = 5  # keep only 5 most recent

def analyze_recommendations():
    if not os.path.exists(SUMMARY_FILE):
        print("[REC] No efficiency summary found.")
        return

    with open(SUMMARY_FILE) as f:
        summary = json.load(f)

    avg = summary.get("avg_exec_time", 0)
    slow_funcs = summary.get("slow_functions", [])
    recs = []

    if avg > 0.2:
        recs.append("Overall latency is high; consider reducing audit interval or caching outputs.")
    if len(slow_funcs) > 3:
        recs.append(f"{len(slow_funcs)} slow functions detected; review for redundant I/O or nested loops.")

    # Function-level advice
    for s in slow_funcs:
        name = s["func"]
        t = s["elapsed"]
        if t > avg * 3:
            recs.append(f"{name} is critically slow ({t:.4f}s). Consider async I/O or background tasking.")
        elif "check_" in name:
            recs.append(f"{name} repeatedly called; consider batching checks.")
        elif "load" in name:
            recs.append(f"{name} may benefit from memoization or caching.")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "recommendations": recs or ["No critical optimizations needed."],
        "source_summary": os.path.basename(SUMMARY_FILE)
    }

    save_report(report)
    print("\n💡 Optimization Recommendations:")
    for r in recs:
        print(" -", r)
    print()

def save_report(report):
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE) as f:
            data = json.load(f)
    else:
        data = []
    data.append(report)
    if len(data) > MAX_REPORTS:
        data = data[-MAX_REPORTS:]  # rotate logs
    with open(REPORT_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[REC] Report saved ({len(data)} total, rotated to keep last {MAX_REPORTS}).")

if __name__ == "__main__":
    analyze_recommendations()
