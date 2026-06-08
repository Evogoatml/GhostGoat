#!/usr/bin/env python3
# modules/diagnostics/diagnostic_center.py

import time, random
from colorama import Fore, Style, init

from core.diagnostics.external_services import ExternalIntelligenceService
from core.brain.agent_core.reasoning_core import record as record_learning
from core.diagnostics.diagnostic_center import record as record_behavior

record_behavior("efficiency_optimization", "success")

# Example inside task execution:
start = time.time()
try:
    # run diagnostic task here
    record_learning("network_connectivity", "success", {"duration": time.time() - start})
except Exception as e:
    record_learning("network_connectivity", "failure", {"error": str(e)})

init(autoreset=True)


def banner():
    icons = ["🧠", "🛰️", "🔐", "⚙️", "🦾", "🧩"]
    print(Fore.CYAN + Style.BRIGHT + f"\n{random.choice(icons)}  ADAPTIVE VAULT DIAGNOSTIC CENTER  {random.choice(icons)}")
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
    print(Fore.BLUE  + " 8️⃣  External Intelligence Sync 🌐")
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
            from core.kernel.engine.efficiency_engine import analyze_efficiency
            analyze_efficiency()
            print(Fore.GREEN + "🧠 Efficiency analysis complete.")
        except Exception as e:
            print(Fore.RED + f"⚠️ Efficiency engine error: {e}")

    elif choice == "10":
        try:
            from core.governance.recommendation_engine import analyze_recommendations
            analyze_recommendations()
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
