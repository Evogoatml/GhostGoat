#!/usr/bin/env python3
import os, sys, time, random
from colorama import Fore, Style, init

# --- Force vault root into import path ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))

print(f"[DEBUG] Adding to sys.path: {VAULT_ROOT}")  # confirm path

if VAULT_ROOT not in sys.path:
    sys.path.insert(0, VAULT_ROOT)

print("[DEBUG] sys.path preview:")
for p in sys.path[:5]:
    print("  ", p)

# --- Imports after sys.path fix ---
from modules.diagnostics.external_services import ExternalIntelligenceService


def banner():
    icons = ["🧠", "🛰️", "🔐", "⚙️", "🦾", "🧩"]
    print(Fore.CYAN + Style.BRIGHT +
          f"\n{random.choice(icons)}  ADAPTIVE VAULT DIAGNOSTIC CENTER  {random.choice(icons)}")
    print(Fore.YELLOW + "═══════════════════════════════════════════════════════════\n")


def section(title, icon="📊", color=Fore.CYAN):
    print(color + f"\n{icon}  {title}")
    print(Fore.YELLOW + "──────────────────────────────────────────────")


def run_diagnostic_menu():
    banner()
    print(Fore.CYAN + "Select a Diagnostic or Optimization Task:\n")
    print(Fore.GREEN + " 1️⃣  System Health Check")
    print(Fore.GREEN + " 2️⃣  Audit Integrity Check")
    print(Fore.GREEN + " 3️⃣  Performance Metrics")
    print(Fore.GREEN + " 4️⃣  Registry Consistency")
    print(Fore.GREEN + " 5️⃣  Log Deduplication")
    print(Fore.GREEN + " 6️⃣  Network Connectivity")
    print(Fore.GREEN + " 7️⃣  Policy Validation")
    print(Fore.BLUE + " 8️⃣  External Intelligence Sync 🌐")
    print(Fore.MAGENTA + " 9️⃣  Efficiency Optimization ⚙️")
    print(Fore.MAGENTA + " 🔟  Generate Optimization Recommendations 💡")
    print(Fore.RED + " 0️⃣  Exit\n")

    choice = input(Fore.WHITE + "Enter option: ").strip()
    section("Executing Task", "🚀", Fore.MAGENTA)

    if choice == "8":
        service = ExternalIntelligenceService()
        try:
            print(Fore.CYAN + "[NET] Checking external intelligence feeds...")
            service.sync(force=True)
            print(Fore.GREEN + "✅ External data sync completed.")
        except PermissionError:
            print(Fore.RED + "🚫 Policy restriction: external data sync not permitted.")
        except Exception as e:
            print(Fore.RED + f"⚠️ External sync error: {e}")

    elif choice == "9":
        try:
            from modules import efficiency_engine
            efficiency_engine.analyze_efficiency()
            print(Fore.GREEN + "🧠 Efficiency analysis complete.")
        except Exception as e:
            print(Fore.RED + f"⚠️ Efficiency engine error: {e}")

    elif choice == "10":
        try:
            from modules import recommondation_engine
            recommondation_engine.analyze_recommendations()
            print(Fore.GREEN + "💡 Recommendations generated successfully.")
        except Exception as e:
            print(Fore.RED + f"⚠️ Recommendation engine error: {e}")

    elif choice == "0":
        print(Fore.YELLOW + "\n🧠 Vault shutting down diagnostics. Stay secure. 🔒\n")
        return False

    else:
        print(Fore.RED + "❌ Invalid selection or module not yet implemented.")

    print(Fore.YELLOW + "\n═══════════════════════════════════════════════════════════\n")
    time.sleep(1)
    return True


if __name__ == "__main__":
    while run_diagnostic_menu():
        pass
