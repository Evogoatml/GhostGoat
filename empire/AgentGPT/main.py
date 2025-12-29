import os
from pathlib import Path
from agent_core.brain.core import AgentCore

def setup_environment():
    print("Setting up AgentCore environment...")
    
    Path("data").mkdir(exist_ok=True)
    Path("audit").mkdir(exist_ok=True)
    Path("keys").mkdir(exist_ok=True)
    
    config_path = Path("config/mission.env")
    config_path.parent.mkdir(exist_ok=True)
    if not config_path.exists():
        print("Creating mission.env stub...")
        with open(config_path, "w") as f:
            f.write("# Configuration variables\n")
            f.write("AUDIT_INTERVAL=10\n")

def main_loop():
    setup_environment()
    
    print("\n--- AgentCore Initialized ---")
    try:
        agent = AgentCore()
        print("Ready. Type 'exit' to quit.")
    except Exception as e:
        print(f"FATAL ERROR during AgentCore initialization. Check if 'sentence-transformers' is installed: {e}")
        return

    user_id = 101
    while True:
        try:
            user_input = input(f"[{user_id}] > ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue

            response = agent.handle(user_id, user_input)
            
            print("\n[AGENT RESPONSE]")
            print(response)
            print("----------------\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main_loop()
