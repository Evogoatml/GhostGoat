#!/usr/bin/env python3
"""🕵 Dataset WS Client"""
import asyncio
import json
import websockets

WS_URL = "ws://localhost:8765"

async def list_datasets():
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({"cmd": "list"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            return json.loads(msg).get("datasets", [])
    except Exception as e:
        return {"error": str(e)}

async def load_dataset(name="swe_lite", limit=10):
    items = []
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({"cmd": "load", "name": name, "limit": limit}))
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                if "done" in data:
                    break
                items.append(data)
    except Exception as e:
        return [{"error": str(e)}]
    return items

async def stream_dataset(name="swe_lite", limit=20, callback=None):
    count = 0
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({"cmd": "stream", "name": name, "limit": limit}))
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                if "stream_done" in data:
                    break
                count += 1
                if callback:
                    callback(data)
    except:
        pass
    return count

if __name__ == "__main__":
    async def test():
        print("Available datasets:")
        for name in await list_datasets():
            print(f"  - {name}")
    
    asyncio.run(test())