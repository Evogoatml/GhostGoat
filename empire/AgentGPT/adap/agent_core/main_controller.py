import importlib
from adap.plugins.api_manager import APIManager
from adap.agent_core import plugin_intel
from adap.modules import memory_vault

class ADAPSystem:
    def __init__(self):
        print("[ADAP] initializing unified system...")
        self.api_manager = APIManager()
        self.plugin_registry = plugin_intel
        self.memory = getattr(memory_vault, "MemoryVault", None)

    def menu(self):
        while True:
            print("""
╔══════════════════════════════════╗
║         ADAP CONTROL PANEL       ║
╠══════════════════════════════════╣
║ 1. API Manager                   ║
║ 2. Plugin Registry               ║
║ 3. Memory Vault (if loaded)      ║
║ 4. Exit                          ║
╚══════════════════════════════════╝
""")
            ch = input("Select option: ").strip()
            if ch == "1":
                importlib.reload(APIManager)
                self.api_manager = APIManager()
                self.api_manager.list_apis()
            elif ch == "2":
                self.plugin_registry.build_registry()
            elif ch == "3":
                if self.memory:
                    print("[Memory] ready.")
                else:
                    print("[Memory] module missing.")
            elif ch == "4":
                print("Exiting.")
                break
            else:
                print("Invalid choice.")

if __name__ == "__main__":
    system = ADAPSystem()
    system.menu()
