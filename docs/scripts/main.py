from dotenv import load_dotenv
load_dotenv('/home/popic/GhostGoat/.env')

import asyncio, requests, time, os
from core.brain.agents.pmmago import build_enterprise_pmmago

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def send_to_telegram(message):
    """Send message to Telegram bot."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"[Telegram Error] {e}", flush=True)

def llm_call(prompt):
    try:
        resp = requests.post('http://localhost:11434/api/chat', 
                           json={'model': 'qwen2.5:0.5b', 
                                 'messages': [{'role': 'user', 'content': prompt}],
                                 'stream': False}, 
                           timeout=60)
        resp.raise_for_status()
        return resp.json()['message']['content']
    except Exception as e:
        return f"Error: {e}"

async def main():
    print("[1] Building orchestrator...", flush=True)
    orch = build_enterprise_pmmago(llm_call, n_workers=1)
    print("[2] Orchestrator built!", flush=True)
    
    send_to_telegram("🚀 GhostGoat Online!")
    
    gen = 0
    while True:
        gen += 1
        print(f"[3] Gen {gen} - Running execute_async...", flush=True)
        result = await orch.execute_async({"description": "test goal"})
        state = result.get("state", {})
        if "direct_response" in state:
            send_to_telegram(f"Gen {gen}: {state['direct_response'][:200]}")
        print(f"[4] Gen {gen} complete! Keys: {list(result.keys())}", flush=True)
        await asyncio.sleep(2)

if __name__ == "__main__":
    print("[0] Starting GhostGoat...", flush=True)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[EXIT] GhostGoat shutting down.", flush=True)
        send_to_telegram("🛑 GhostGoat Offline")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
