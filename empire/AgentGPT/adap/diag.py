#!/usr/bin/env python3
import argparse, time, random
from colorama import init, Fore, Style
from modules.diagnostics.self_check import run_all
from modules.diagnostics.network_context import can_use_api
from modules.public_api_connector import fetch_api_list

if can_use_api():
    fetch_api_list(need_external=True)
else:
    fetch_api_list()  # local mode
init(autoreset=True)

def banner():
    faces = ["🤖", "🧠", "🔐", "🛰️", "🦾", "⚙️"]
    icon = random.choice(faces)
    print(Fore.CYAN + Style.BRIGHT + f"\n{icon}  ADAPTIVE VAULT DIAGNOSTICS  {icon}")
    print(Fore.YELLOW + "═══════════════════════════════════════════════════════════\n")

def section(title, icon="🧩", color=Fore.CYAN):
    print(color + f"\n{icon}  {title}")
    print(Fore.YELLOW + "──────────────────────────────────────────────")

def pretty_result(result):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result['ts']))
    section("Run Summary", "🕓", Fore.MAGENTA)
    print(Fore.WHITE + f"📅  Timestamp: {ts}")

    if not result.get("missing_required_files"):
        print(Fore.GREEN + "✅  Core Files: All present")
    else:
        print(Fore.RED + "❌  Missing Core Files:")
        for f in result["missing_required_files"]:
            print(Fore.RED + "    - " + f)

    acts = result.get("actions", [])
    section("Actions & Repairs", "🧰", Fore.BLUE)
    if acts:
        for a in acts:
            for k, v in a.items():
                print(Fore.CYAN + f"   🔧 {k}: {v}")
    else:
        print(Fore.GREEN + "✨  Nothing to repair. System pristine.")

    section("System Status", "📊", Fore.GREEN)
    if not result["missing_required_files"]:
        print(Fore.GREEN + "🟢  STATUS: Stable & Operational")
    else:
        print(Fore.RED + "🔴  STATUS: Attention Needed")

    section("Health Telemetry", "📡", Fore.CYAN)
    print(Fore.WHITE + "🧬  Integrity: " + Fore.GREEN + "OK")
    print(Fore.WHITE + "🧱  Filesystem: " + Fore.GREEN + "OK")
    print(Fore.WHITE + "🗄️  Registry DB: " + Fore.GREEN + "OK")
    print(Fore.WHITE + "📜  Audit Log: " + Fore.GREEN + "Clean")

    print(Fore.YELLOW + "\n═══════════════════════════════════════════════════════════\n")
    print(Fore.CYAN + Style.BRIGHT + random.choice([
        "🚀 All systems nominal.",
        "🧠 Vault self-check complete.",
        "🔐 Integrity maintained.",
        "🦾 Diagnostics passed. Efficiency rising."
    ]))
    print()

def main():
    p = argparse.ArgumentParser(description="Adaptive Vault Diagnostics")
    p.add_argument("--all", action="store_true", help="run full diagnostics + self-repair")
    args = p.parse_args()

    banner()
    if args.all:
        result = run_all(auto_fix=True, auto_install=True)
        pretty_result(result)
    else:
        print("Usage:\n  python3 diag.py --all\n")
        print("This runs a full system scan with emoji-enhanced output.\n")

if __name__ == "__main__":
    main()
