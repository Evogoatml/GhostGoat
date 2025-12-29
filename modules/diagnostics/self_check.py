
import os, json

def run_all():
    checks = {
        "folders": ["adap/agent_core", "adap/plugins", "adap/modules", "adap/data"],
        "files": ["adap/requirements.txt", "adap/README.md"]
    }
    results = {}
    for folder in checks["folders"]:
        results[folder] = os.path.isdir(folder)
    for file in checks["files"]:
        results[file] = os.path.isfile(file)

    missing = [k for k, v in results.items() if not v]
    if missing:
        print("⚠ Missing components:", missing)
    else:
        print("✅ All structure verified.")
    return results
