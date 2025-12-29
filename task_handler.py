# modules/task_handler.py
from modules.governance.decision_governor import enforce
from modules.google_integration import run_google_task
from modules.diagnostics.efficiency_engine import analyze_efficiency

def handle_task(task):
    print(f"[TASK] Received: {task}")
    
    if "google" in task.lower():
        enforce("google_api", run_google_task)
    elif "efficiency" in task.lower():
        enforce("efficiency", analyze_efficiency)
    else:
        print("[TASK] No known module assigned for that task.")
