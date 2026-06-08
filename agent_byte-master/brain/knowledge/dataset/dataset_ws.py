#!/usr/bin/env python3
"""🕵 Dataset WebSocket Server - Lazy load all datasets"""
import json
import asyncio
from websockets import serve as ws_serve

PORT = 8765

ALL_DATASETS = {
    "swe_lite": {"hf": "princeton-nlp/SWE-bench_Lite", "split": "test"},
    "pentest_eval": {"hf": "preemware/pentesting-eval", "split": "train"},
    "pentest_alpaca": {"hf": "preemware/pentest-agent-dataset-alpaca", "split": "train"},
    "agent_training": {"hf": "ObisDevs/Agent_Training_Dataset", "split": "train"},
}

def load_dataset(name, limit=10):
    try:
        cfg = ALL_DATASETS[name]
        from datasets import load_dataset
        ds = load_dataset(cfg["hf"], split=f"{cfg['split']}[:{limit}]")
        return [{"source": name, "id": str(i), **{k: str(v)[:300] for k, v in ex.items()}} 
                for i, ex in enumerate(ds)]
    except Exception as e:
        return [{"error": str(e)}]

async def handler(ws):
    try:
        msg = await ws.recv()
        data = json.loads(msg)
        cmd = data.get("cmd", "")
        
        if cmd == "list":
            await ws.send(json.dumps({"datasets": list(ALL_DATASETS.keys())}))
        
        elif cmd == "load":
            name = data.get("name", "swe_lite")
            limit = min(data.get("limit", 10), 100)
            for item in load_dataset(name, limit):
                await ws.send(json.dumps(item))
            await ws.send(json.dumps({"done": True}))
        
        else:
            await ws.send(json.dumps({"error": f"Unknown: {cmd}"}))
    
    except Exception as e:
        await ws.send(json.dumps({"error": str(e)}))

async def main():
    print(f"🕵 Dataset WS on ws://localhost:{PORT}")
    async with ws_serve(handler, "localhost", PORT):
        await asyncio.sleep(99999)

if __name__ == "__main__":
    asyncio.run(main())