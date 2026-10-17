"""Casual Telegram chat must NOT create tasks; /goal runs the task pipeline.

Plain text -> one chat reply (no task, no thought records).
/goal <text> -> full orchestrator pipeline (creates a task).
"""

import asyncio

from services.telegram_bot import HELP_TEXT, TelegramBotService

_UNSET = object()


class FakeConfig:
    bot_token = ""  # transport idle: handle_update still returns the reply
    chat_ids = [111]
    webhook_secret = ""
    webhook_url = ""


def make_bot(chat_fn=_UNSET):
    calls = {"goals": [], "chats": []}

    async def process_goal(goal, context):
        calls["goals"].append((goal, context))
        return {"id": "task-1", "status": "completed", "result": {"result": "done"}}

    async def default_chat(chat_id, text, history):
        calls["chats"].append((chat_id, text, history))
        return "chat reply"

    bot = TelegramBotService(
        FakeConfig(),
        process_goal=process_goal,
        get_status=lambda: {},
        get_agents=lambda: {},
        get_memory=lambda: {},
        chat=default_chat if chat_fn is _UNSET else chat_fn,
    )
    return bot, calls


def send(bot, text, chat_id=111):
    return asyncio.run(bot.handle_update({"message": {"chat": {"id": chat_id}, "text": text}}))


def test_plain_text_is_chat_and_creates_no_task():
    bot, calls = make_bot()
    assert send(bot, "hello there") == "chat reply"
    assert len(calls["chats"]) == 1
    assert calls["goals"] == []


def test_goal_runs_full_task_pipeline():
    bot, calls = make_bot()
    reply = send(bot, "/goal clean the shed")
    assert reply == "done"
    assert calls["chats"] == []
    assert len(calls["goals"]) == 1
    goal, context = calls["goals"][0]
    assert goal == "clean the shed"
    assert context["source"] == "telegram"
    assert context["chat_id"] == "111"


def test_goal_without_argument_shows_usage():
    bot, calls = make_bot()
    reply = send(bot, "/goal")
    assert "usage" in reply.lower()
    assert calls["goals"] == [] and calls["chats"] == []


def test_unknown_command_shows_help_not_chat():
    bot, calls = make_bot()
    assert send(bot, "/bogus x") == HELP_TEXT
    assert calls["goals"] == [] and calls["chats"] == []


def test_help_mentions_goal_and_chat_behavior():
    assert "/goal" in HELP_TEXT
    assert "no task is created" in HELP_TEXT


def test_chat_rate_limit_returns_friendly_message():
    async def rate_limited(chat_id, text, history):
        return None

    bot, calls = make_bot(chat_fn=rate_limited)
    reply = send(bot, "tell me a joke")
    assert "too fast" in reply
    assert calls["goals"] == []


def test_chat_provider_429_is_friendly():
    async def provider_busy(chat_id, text, history):
        raise RuntimeError("429 Too Many Requests")

    bot, _ = make_bot(chat_fn=provider_busy)
    assert "busy" in send(bot, "hi").lower()


def test_chat_failure_is_reported_not_raised():
    async def broken(chat_id, text, history):
        raise RuntimeError("boom")

    bot, _ = make_bot(chat_fn=broken)
    assert "failed" in send(bot, "hi").lower()


def test_chat_not_wired_points_to_goal():
    bot, _ = make_bot(chat_fn=None)
    assert "Chat isn't wired" in send(bot, "hi")


def test_chat_history_accumulates_across_messages():
    bot, calls = make_bot()
    send(bot, "first message")
    send(bot, "second message")
    assert len(calls["chats"]) == 2
    first_exchange = [
        {"role": "user", "content": "first message"},
        {"role": "assistant", "content": "chat reply"},
    ]
    assert calls["chats"][1][2] == first_exchange


def test_unauthorized_chat_is_ignored():
    bot, calls = make_bot()
    assert send(bot, "hello", chat_id=999) is None
    assert calls["goals"] == [] and calls["chats"] == []
