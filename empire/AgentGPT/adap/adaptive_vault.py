#!/usr/bin/env python3
# adaptive_vault.py — live adaptive console

from translator_gate import process_upload
from policy import choose_cipher
from crypto import encrypt, sign_log
from monitor import get_resource_state
from datetime import datetime
from modules.api_registry import find_api, update_cache
from modules.learning.neural_core import NeuralCore
import json, time, os

# --- Initialize neural core memory and API cache ---
core = NeuralCore()
update_cache()
apis = find_api("security")

_last_diag = 0

def maybe_run_diag():
    """Light periodic diagnostics every ~10 minutes."""
    global _last_diag
    now = time.time()
    if now - _last_diag > 600:
        try:
            from modules.diagnostics.self_check import run_all
            run_all(auto_fix=True, auto_install=False)
        except Exception as e:
            print(f"[WARN] Diagnostics failed: {e}")
        _last_diag = now


def load_env(path):
    """Load mission environment variables."""
    env = {}
    if not os.path.exists(path):
        print("[ERROR] mission.env not found")
        return env
    with open(path) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def log_state(gate_status, cpu, cipher, message=""):
    """Console-friendly live system status output."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] GATE: {gate_status:<10} | CPU: {cpu:>5.1f}% | Cipher: {cipher:<8} | {message}")


def main():
    base_dir = os.getcwd()
    mission = load_env(os.path.join(base_dir, "mission.env"))
    print("[INIT] Mission loaded:", mission.get("MISSION", "unknown"))

    while True:
        try:
            manifest_path = os.path.join(base_dir, "manifest.json")
            sig_path = os.path.join(base_dir, "manifest.sig")
            artifact_path = os.path.join(base_dir, "artifact.bin")

            # Learning event — awareness of system loop health
            core.record_experience("core_loop", "success")

            # Check required files
            if not all(os.path.exists(p) for p in [manifest_path, sig_path, artifact_path]):
                log_state("waiting", 0.0, "-", "No input files detected")
                time.sleep(5)
                continue

            # Run translator gate
            res = process_upload(manifest_path, sig_path, artifact_path)
            gate_status = res.get("status", "error")

            if gate_status != "allow":
                core.record_experience("translator_gate", "failure")
                log_state(gate_status, 0.0, "-", "Quarantined or rejected")
                time.sleep(5)
                continue

            core.record_experience("translator_gate", "success")

            # Gather metrics & choose cipher
            metrics = get_resource_state()
            cipher = choose_cipher(metrics, mission)
            cpu = metrics.get("cpu", 0.0)

            # Reinforcement signal: performance success
            core.record_experience("efficiency_engine", "success", latency=cpu / 10 or 1.0)

            entry = {"ts": time.time(), "cpu": cpu, "cipher": cipher}
            signed_entry = sign_log(entry)
            with open(os.path.join(base_dir, "audit.log"), "a") as f:
                f.write(json.dumps(signed_entry) + "\n")

            log_state(gate_status, cpu, cipher, "System active")
            maybe_run_diag()
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n[CTRL+C] Graceful shutdown...")
            break
        except Exception as e:
            core.record_experience("core_loop", "failure")
            log_state("error", 0.0, "-", f"GATE ERROR: {e}")
            time.sleep(5)

    # Post-run self-reflection
    print("\n[SHUTDOWN] Reflecting on recent performance...")
    core.introspect()
