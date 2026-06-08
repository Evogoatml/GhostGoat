"""GhostGoat SSE Streaming — Server-Sent Events for real-time execution output."""
import asyncio, json, logging, time
from typing import Any, AsyncGenerator, Dict, Optional
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

class StreamManager:
    def __init__(self):
        self.queues: list = []
        self.history: list = []

    async def broadcast(self, event_type: str, payload: Dict[str, Any]):
        msg = f"event: {event_type}\ndata: {json.dumps(payload, default=str)}\n\n"
        self.history.append({"type": event_type, "payload": payload, "ts": time.time()})
        dead = []
        for q in self.queues:
            try:
                await q.put(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            self.queues.remove(q)

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self.queues:
            self.queues.remove(q)

    async def event_generator(self, q: asyncio.Queue) -> AsyncGenerator[str, None]:
        try:
            while True:
                msg = await q.get()
                if msg is None:
                    break
                yield msg
        except asyncio.CancelledError:
            pass
        finally:
            self.unsubscribe(q)

stream_manager = StreamManager()

def register_sse_routes(app: FastAPI):
    @app.get("/v2/stream")
    async def sse_stream():
        q = stream_manager.subscribe()
        return StreamingResponse(stream_manager.event_generator(q), media_type="text/event-stream")

    @app.post("/v2/stream/goal")
    async def stream_goal(goal: str):
        async def _run():
            await stream_manager.broadcast("goal_start", {"goal": goal, "timestamp": time.time()})
            await asyncio.sleep(0.5)
            await stream_manager.broadcast("goal_complete", {"goal": goal, "status": "done"})
        asyncio.create_task(_run())
        return {"status": "started"}

    logger.info("SSE routes registered: /v2/stream, /v2/stream/goal")

