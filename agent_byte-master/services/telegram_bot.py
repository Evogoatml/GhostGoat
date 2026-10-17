"""Telegram bot service wired to the real GhostGoat orchestrator.

Flow: Telegram -> /api/telegram/webhook (or long polling) -> orchestrator
``process_goal`` -> response -> Telegram ``sendMessage``.

The service is registered under the orchestrator and is transport only. The
orchestrator behind it is injected, so the bot, the API and the dashboard all
share one orchestrator instance. Without a token the Telegram network transport
stays idle, but inbound webhook updates are still dispatched to the orchestrator
and answered in the HTTP response.
"""

import asyncio
import hmac
import json
import logging
import urllib.request
from collections import deque
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("ghostgoat.telegram")

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LEN = 4096
HISTORY_LIMIT = 20
POLL_TIMEOUT = 25

HELP_TEXT = (
    "GhostGoat orchestrator bot\n"
    "Just send text to chat — casual messages get a plain reply, no task is created.\n"
    "/goal <text> - run a full agent goal (creates a task)\n"
    "/status - orchestrator and agent status\n"
    "/agents - agent fleet\n"
    "/memory - knowledge and memory stats\n"
    "/history - recent goals in this chat\n"
    "/help - this message"
)

ProcessGoal = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]
StatusProvider = Callable[[], Dict[str, Any]]
# chat(chat_id, text, recent_history) -> reply, or None when rate-limited
ChatFn = Callable[[str, str, List[Dict[str, Any]]], Awaitable[Optional[str]]]


class TelegramBotService:
    """Routes Telegram messages to the orchestrator and reports state back."""

    def __init__(
        self,
        config: Any,
        process_goal: ProcessGoal,
        get_status: StatusProvider,
        get_agents: StatusProvider,
        get_memory: StatusProvider,
        api_base: str = TELEGRAM_API,
        chat: Optional[ChatFn] = None,
    ):
        self.config = config
        self._process_goal = process_goal
        self._chat_fn = chat
        self._get_status = get_status
        self._get_agents = get_agents
        self._get_memory = get_memory
        self.api_base = api_base.rstrip("/")
        self.conversations: Dict[str, Deque[Dict[str, Any]]] = {}
        self.chat_history: Dict[str, Deque[Dict[str, str]]] = {}
        self._poll_task: Optional[asyncio.Task] = None
        self._offset = 0

    @property
    def enabled(self) -> bool:
        return bool(self.config.bot_token)

    def is_allowed(self, chat_id: Any) -> bool:
        """Only configured chats/groups may talk to the orchestrator."""
        return str(chat_id) in {str(c) for c in self.config.chat_ids}

    def verify_secret(self, header_value: Optional[str]) -> bool:
        secret = self.config.webhook_secret
        if not secret:
            return True
        return hmac.compare_digest(secret, header_value or "")

    # -- Telegram transport -------------------------------------------------

    def _call_sync(self, method: str, payload: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
        url = f"{self.api_base}/bot{self.config.bot_token}/{method}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec - fixed Telegram host
            return json.loads(response.read().decode())

    async def _call(self, method: str, payload: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
        try:
            return await asyncio.to_thread(self._call_sync, method, payload, timeout)
        except Exception as exc:  # never leak the token embedded in the URL
            logger.warning("Telegram %s failed: %s", method, type(exc).__name__)
            return {"ok": False}

    async def send_message(self, chat_id: Any, text: str) -> None:
        text = text or "(empty)"
        for start in range(0, len(text), MAX_MESSAGE_LEN):
            await self._call("sendMessage", {"chat_id": chat_id, "text": text[start:start + MAX_MESSAGE_LEN]})

    async def notify(self, text: str) -> None:
        """Broadcast an orchestrator state change to every configured chat."""
        if not self.enabled:
            return
        for chat_id in self.config.chat_ids:
            await self.send_message(chat_id, text)

    async def on_orchestrator_event(self, event: Dict[str, Any]) -> None:
        """Report orchestrator task, agent, memory and graph events to the chats."""
        if (event.get("data") or {}).get("source") == "telegram":
            return
        await self.notify(self.format_event(event))

    @staticmethod
    def format_event(event: Dict[str, Any]) -> str:
        kind = event.get("type")
        data = event.get("data") or {}
        if kind == "task":
            return TelegramBotService.format_task(data)
        if kind == "memory":
            return f"Memory updated: {data.get('stats')}"
        if kind == "graph":
            return f"Graph updated: {data.get('nodes')} nodes, {data.get('edges')} edges"
        if kind == "agent":
            return f"Agent {data.get('agent_id')} is {data.get('status')}"
        return f"{kind}: {json.dumps(data, default=str)}"

    # -- Message handling ---------------------------------------------------

    async def handle_update(self, update: Dict[str, Any]) -> Optional[str]:
        """Process one Telegram update; returns the reply that was sent."""
        message = update.get("message") or update.get("edited_message") or update.get("channel_post")
        if not message:
            return None
        chat_id = (message.get("chat") or {}).get("id")
        text = (message.get("text") or "").strip()
        if chat_id is None or not text:
            return None
        if not self.is_allowed(chat_id):
            logger.warning("Ignoring message from unauthorized chat %s", chat_id)
            return None

        reply = await self._route(str(chat_id), text)
        if self.enabled:
            await self.send_message(chat_id, reply)
        return reply

    async def _route(self, chat_id: str, text: str) -> str:
        command = text.split()[0].split("@")[0].lower() if text.startswith("/") else None
        if command in ("/start", "/help"):
            return HELP_TEXT
        if command == "/status":
            return self._format("Status", self._get_status)
        if command == "/agents":
            return self._format("Agents", self._get_agents)
        if command == "/memory":
            return self._format("Memory", self._get_memory)
        if command == "/history":
            return self._format_history(chat_id)
        if command == "/goal":
            parts = text.split(None, 1)
            goal = parts[1].strip() if len(parts) > 1 else ""
            if not goal:
                return "Usage: /goal <what you want done>"
            return await self._run_goal(chat_id, goal)
        if command:
            return HELP_TEXT
        # Plain text = casual chat: one LLM reply, no task, no thought records.
        return await self._chat_reply(chat_id, text)

    async def _chat_reply(self, chat_id: str, text: str) -> str:
        """Casual conversational reply — never touches the task pipeline."""
        if self._chat_fn is None:
            return "Chat isn't wired — use /goal <description> to run a full goal."
        history = self.chat_history.setdefault(chat_id, deque(maxlen=HISTORY_LIMIT))
        try:
            reply = await self._chat_fn(chat_id, text, list(history)[-5:])
        except Exception as exc:
            logger.exception("Telegram chat failed")
            msg = str(exc)
            if "429" in msg or "rate limit" in msg.lower() or "too many requests" in msg.lower():
                return "⏳ The AI service is busy. Please try again in a moment."
            return "❌ Chat failed — please try again."
        if reply is None:
            return "⏳ You're sending messages too fast — slow down a moment."
        reply = (reply or "").strip() or "(empty)"
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        return reply

    async def _run_goal(self, chat_id: str, goal: str) -> str:
        history = self.conversations.setdefault(chat_id, deque(maxlen=HISTORY_LIMIT))
        context = {"source": "telegram", "chat_id": chat_id, "history": list(history)[-5:]}
        try:
            task = await self._process_goal(goal, context)
        except Exception as exc:
            logger.exception("Orchestrator failed for telegram goal")
            error_msg = str(exc)
            if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                task = {"id": None, "status": "rate_limited", "result": {"error": "The AI service is currently busy. Please try again in a moment."}}
            else:
                task = {"id": None, "status": "failed", "result": {"error": error_msg}}
        
        # Also check task result for rate limit errors (orchestrator returns failed tasks, not exceptions)
        if task.get("status") == "failed":
            result = task.get("result", {})
            error_msg = str(result.get("error", "")) if isinstance(result, dict) else str(result)
            if "429" in error_msg or "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                task = {"id": task.get("id"), "status": "rate_limited", "result": {"error": "The AI service is currently busy. Please try again in a moment."}}
        
        history.append({
            "goal": goal,
            "task_id": task.get("id"),
            "status": task.get("status"),
            "time": datetime.now(timezone.utc).isoformat(),
        })
        return self.format_task(task)

    @staticmethod
    def format_task(task: Dict[str, Any]) -> str:
        result = task.get("result")
        status = task.get('status')
        
        if status == "rate_limited":
            return "⏳ The AI service is busy. Please wait a moment and try again."
        
        if status == "busy":
            return "🤖 All agents are busy right now. Please try again in a moment."

        if status == "budget_exhausted":
            return "🛑 Daily task budget reached. Please try again tomorrow."
        
        if status == "failed":
            if isinstance(result, dict):
                error = result.get("error", "Unknown error")
            else:
                error = str(result)
            return f"❌ Sorry, I couldn't process that: {error}"
        
        if status == "completed":
            if isinstance(result, dict):
                # Extract the actual response content
                body = result.get("result") or result.get("output") or result.get("response") or result.get("text")
                if body:
                    return str(body)
                # Fallback: try to find any meaningful content
                for key in ["content", "message", "answer", "reply"]:
                    if key in result and result[key]:
                        return str(result[key])
                # Last resort: pretty print the dict (but avoid raw technical output)
                return "✅ Task completed successfully."
            else:
                return str(result)
        
        # Default for other statuses
        return f"Status: {status}"

    @staticmethod
    def _format(title: str, provider: StatusProvider) -> str:
        try:
            return f"{title}\n{json.dumps(provider(), indent=2, default=str)}"
        except Exception as exc:
            return f"{title}: error ({exc})"

    def _format_history(self, chat_id: str) -> str:
        history = self.conversations.get(chat_id)
        if not history:
            return "No goals yet in this chat."
        return "\n".join(f"- [{h['status']}] {h['goal'][:80]}" for h in history)

    # -- Lifecycle ----------------------------------------------------------

    async def start(self) -> bool:
        """Connect the Telegram transport (webhook or polling) for the configured token."""
        if not self.enabled:
            logger.warning("TELEGRAM_BOT_TOKEN not set: transport idle, webhook dispatch only")
            return False
        if self.config.webhook_url:
            payload: Dict[str, Any] = {"url": self.config.webhook_url}
            if self.config.webhook_secret:
                payload["secret_token"] = self.config.webhook_secret
            await self._call("setWebhook", payload)
            logger.info("Telegram webhook registered")
        else:
            await self._call("deleteWebhook", {})
            self._poll_task = asyncio.create_task(self._poll_loop())
            logger.info("Telegram long polling started")
        await self.notify("GhostGoat online")
        return True

    async def stop(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        if self.enabled:
            await self.notify("GhostGoat offline")

    async def _poll_loop(self) -> None:
        while True:
            response = await self._call(
                "getUpdates",
                {"offset": self._offset, "timeout": POLL_TIMEOUT},
                timeout=POLL_TIMEOUT + 10,
            )
            if not response.get("ok"):
                await asyncio.sleep(5)
                continue
            for update in response.get("result", []):
                self._offset = update["update_id"] + 1
                try:
                    await self.handle_update(update)
                except Exception:
                    logger.exception("Failed to handle telegram update")
