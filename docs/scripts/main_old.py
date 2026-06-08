from dotenv import load_dotenv
load_dotenv('/home/popic/GhostGoat/.env')

import asyncio, signal, sys, time, os, subprocess, requests, json

def get_hardware_strategy():
    """Dynamically resolves hardware without crashing on import."""
    try:
        import torch_xla.core.xla_model as xm
        return xm.xla_device(), xm.master_print
    except ImportError:
        try:
            import torch
            dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            return dev, print
        except ImportError:
            print("\033[91m[Error]\033[0m PyTorch not found. Run: pip install torch")
            sys.exit(1)

from core.brain.agents.pmmago import build_enterprise_pmmago

CFG = {
    "n_workers": 1,  # Reduced workers to minimize LLM calls
    "auto_patch": True,
    "path": "/home/popic/GhostGoat/",
    "services": [],  # Disable services to avoid import errors; can re-enable after fixing missing modules
    "evolution_goal": "Self-optimize PMMAGO core logic for 8t TPU matrix units",
    "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "")
}

PROCS = []

def manage_service(name, action="start"):
     if action == "kill": return [p.kill() for p in PROCS]
     script_path = os.path.join(CFG["path"], "services", f"{name}.py")
     print(f"[DEBUG] Managing service {name}: script_path={script_path}", flush=True)
     if os.path.exists(script_path):
         print(f"[DEBUG] Starting service {name} with {sys.executable} {script_path}", flush=True)
         return subprocess.Popen([sys.executable, script_path])
     else:
         print(f"[DEBUG] Service {name} script not found at {script_path}", flush=True)
     return None

def send_to_telegram(message):
    """Send message to Telegram bot."""
    if not CFG["telegram_token"] or not CFG["telegram_chat_id"]:
        return
    try:
        url = f"https://api.telegram.org/bot{CFG['telegram_token']}/sendMessage"
        requests.post(url, json={"chat_id": CFG["telegram_chat_id"], "text": message}, timeout=10)
    except Exception as e:
        print(f"[Telegram Error] {e}", flush=True)

async def run_fused_engine():
    print("[DEBUG] Entering run_fused_engine", flush=True)
    # Only orchestrator makes LLM calls via this function
    def llm_call(prompt):
        try:
            response = requests.post('http://localhost:11434/api/chat', 
                                   json={'model': 'qwen2.5:0.5b', 
                                         'messages': [{'role': 'user', 'content': prompt}],
                                         'stream': False}, 
                                   timeout=180)
            response.raise_for_status()
            return response.json()['message']['content']
        except Exception as e:
            return f"Error: {e}"
    
    device, logger = get_hardware_strategy()
    print(f"[DEBUG] Got device: {device}", flush=True)
    
    # Build orchestrator with single LLM call function
    orch = build_enterprise_pmmago(llm_call, n_workers=CFG["n_workers"])
    print("[DEBUG] Orchestrator built", flush=True)
    orch.auto_patch = CFG["auto_patch"]
    
    logger(f"📡 Hardware Engaged: {device}")
    send_to_telegram(f"🚀 GhostGoat Online - Hardware: {device}")
    print("[DEBUG] Before while loop", flush=True)
    
    gen = 0
    print("[DEBUG] Entering while loop", flush=True)
    while True:
        gen += 1
        print(f"[DEBUG] Gen {gen}", flush=True)
        logger(f"🔄 Gen {gen} - Unfolding NeoVertex1 Axioms...")
        try:
            result = await orch.execute_async({"description": CFG["evolution_goal"]})
            # Send summary to Telegram
            state = result.get("state", {})
            if "direct_response" in state:
                send_to_telegram(f"Gen {gen}: {state['direct_response'][:200]}")
        except Exception as e:
            logger(f"⚠️ Execution Error: {e}")
            import traceback
            traceback.print_exc()
            send_to_telegram(f"⚠️ Error in Gen {gen}: {str(e)[:100]}")
        
        for p in PROCS:
            if p and p.poll() is not None:
                logger(f"⚠️ Node {p.pid} dropped. Re-engaging...")
        await asyncio.sleep(2)

def cleanup(*_):
    print("\n\033[93m[GhostGoat]\033[0m Shutting down all nodes...")
    manage_service("", "kill")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    for service in CFG["services"]:
        proc = manage_service(service)
        if proc: PROCS.append(proc)
    
    print("\033[92m[GhostGoat]\033[0m Engine Online. Running 24/7.\n", flush=True)
    print("[DEBUG] About to call asyncio.run()", flush=True)
    try:
        asyncio.run(run_fused_engine())
        print("[DEBUG] asyncio.run() returned!", flush=True)
    except Exception as e:
        print(f"💀 Fatal Exception: {e}", flush=True)
        import traceback
        traceback.print_exc()
        cleanup()
    except BaseException as e:
        print(f"💀 Fatal BaseException: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        cleanup()
