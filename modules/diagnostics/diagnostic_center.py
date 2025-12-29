
import time
from . import self_check, network_context

def run():
    print("\n🧠 adap Diagnostic Center")
    print("==========================")
    print("1. Self-check")
    print("2. Network test")
    print("3. Full scan")
    print("4. Exit")
    while True:
        opt = input("Select> ").strip()
        if opt == "1":
            self_check.run_all()
        elif opt == "2":
            network_context.can_use_api()
        elif opt == "3":
            print("Running full scan...")
            self_check.run_all()
            network_context.can_use_api()
            print("✅ Diagnostics complete.")
        elif opt == "4":
            break
        else:
            print("Invalid option.")
        time.sleep(0.5)
