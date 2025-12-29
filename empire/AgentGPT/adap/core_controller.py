#!/usr/bin/env python3
# adaptive_vault/core_controller.py

import importlib, traceback, time, json
from datetime import datetime

class ModuleWrapper:
    def __init__(self, name):
        self.name = name
        self.module = None

    def load(self):
        try:
            self.module = importlib.import_module(f"modules.{self.name}")
            print(f"[LOAD ✅] {self.name}")
            return True
        except Exception as e:
            print(f"[LOAD ⚠️] {self.name} failed: {e}")
            self.module = None
            return False

    def call(self, func_name, *args, **kwargs):
        if not self.module:
            return None
        try:
            func = getattr(self.module, func_name)
            return func(*args, **kwargs)
        except Exception:
            print(f"[EXEC ⚠️] {self.name}.{func_name} error:")
            traceback.print_exc()
            return None


class AdaptiveVault:
    def __init__(self):
        self.modules = {
            "governance.decision_governor": ModuleWrapper("governance.decision_governor"),
            "efficiency_engine": ModuleWrapper("efficiency_engine"),
            "diagnostics.self_check": ModuleWrapper("diagnostics.self_check")
        }

    def startup(self):
        print("\n🧠 Booting Adaptive Vault...")
        for mod in self.modules.values():
            mod.load()
        print("[CORE] Initialization complete.\n")

    def main_loop(self):
        while True:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Running system cycle...")
            
            # Example of guarded calls
            diag = self.modules["diagnostics.self_check"].call("run_all", auto_fix=True)
            if diag:
                print(json.dumps(diag, indent=2))

            time.sleep(10)


if __name__ == "__main__":
    vault = AdaptiveVault()
    vault.startup()
    vault.main_loop()
