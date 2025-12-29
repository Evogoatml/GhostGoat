# main.py
# Adaptive Vault framework entrypoint with dynamic module auto-loader

import sys, os, importlib, time

# define base paths
BASE_DIR = os.path.dirname(__file__)
CORE_DIR = os.path.join(BASE_DIR, "core")
MODULE_DIR = os.path.join(BASE_DIR, "modules")

# add paths so imports work globally
sys.path.extend([CORE_DIR, MODULE_DIR])

# --- MODULE AUTO-LOADER -------------------------------------------------------

def load_modules(mod_path):
    """Dynamically import all Python modules in the /modules folder."""
    print(f"[SYSTEM] Scanning {mod_path} for modules...")
    loaded = []
    for file in os.listdir(mod_path):
        if not file.endswith(".py") or file.startswith("__"):
            continue
        mod_name = file[:-3]
        try:
            mod = importlib.import_module(mod_name)
            loaded.append(mod_name)
        except Exception as e:
            print(f"[WARN] Failed to load module '{mod_name}': {e}")
    if loaded:
        print(f"[MODULES ACTIVE] {', '.join(loaded)}")
    else:
        print("[MODULES] No modules found.")
    return loaded

# --- CORE VAULT INITIALIZATION -----------------------------------------------

def start_vault():
    """Import and launch the adaptive vault main loop."""
    try:
        from adaptive_vault import main as vault_main
    except Exception as e:
        print(f"[ERROR] Core vault could not be imported: {e}")
        return
    print("[SYSTEM] Adaptive Vault core initializing...")
    vault_main()

# --- EXECUTION FLOW -----------------------------------------------------------

if __name__ == "__main__":
    print("="*65)
    print("🧠 Adaptive Vault — Modular Intelligence Framework")
    print("="*65)
    print(f"[BOOT] Starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    modules_loaded = load_modules(MODULE_DIR)
    print("[BOOT] Loading core system...")
    start_vault()
