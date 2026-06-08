#!/usr/bin/env python3
"""
GhostGoat Telegram Interface — wired to brain/system.py (simple chat system).

Uses: from brain.system import system
      await system.chat(message=..., user_id=..., username=..., history=...)
"""
import os, sys, asyncio
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from brain.system import system
from typing import Any

try:
    from telegram import Update
    from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
    _HAS_TELEGRAM = True
except ImportError:
    _HAS_TELEGRAM = False
    Update = Any
    ContextTypes = Any
    Application = Any
    MessageHandler = Any
    CommandHandler = Any
    filters = Any
    print("[WARN] python-telegram-bot not installed. Run: pip install python-telegram-bot")

# Load .env from project root (one level above agent_byte-master)
env = {}
_env_path = _ROOT.parent / '.env'
if not _env_path.is_file():
    _env_path = _ROOT / '.env'
if _env_path.is_file():
    with open(_env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v
                os.environ.setdefault(k, v)

# Per-user history
_history: dict = {}


async def _send(message, text: str):
    if len(text) > 4000:
        for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            await message.reply_text(chunk, parse_mode="Markdown")
    else:
        await message.reply_text(text, parse_mode="Markdown")


async def _chat(update: Update, text: str):
    uid = update.effective_user.id
    username = update.effective_user.first_name or "friend"

    history = _history.setdefault(uid, [])
    history.append(text)
    if len(history) > 20:
        history.pop(0)

    try:
        result = await system.chat(
            message=text,
            user_id=uid,
            username=username,
            history=[{"role": "user", "content": h} for h in history[:-1]],
        )
        await _send(update.message, result.get("text", "No response"))
    except Exception as e:
        import traceback
        traceback.print_exc()
        await _send(update.message, f"❌ Error: {str(e)[:200]}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _chat(update, update.message.text.strip())


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _chat(update, update.message.text.strip())


async def handle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _history.pop(uid, None)
    await update.message.reply_text("🗑️ Conversation reset.")


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🧠 *GhostGoat Status*\n"
        f"System: brain/system.py\n"
        f"LLM: {system.config.llm_provider}/{system.config.llm_model}\n"
        f"Intelligence: {'available' if hasattr(system, 'ability_manager') else 'stub'}"
    , parse_mode="Markdown")


def main():
    if not _HAS_TELEGRAM:
        print("❌ Cannot start: python-telegram-bot not installed")
        return

    token = env.get('TELEGRAM_BOT_TOKEN', '')
    if not token or 'your' in token.lower():
        print("❌ TELEGRAM_BOT_TOKEN missing or invalid")
        return

    print("🐐 GhostGoat Telegram Bot starting...", flush=True)
    print(f"✓ brain/system.py ready", flush=True)
    print(f"✓ LLM: {system.config.llm_provider}/{system.config.llm_model}", flush=True)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("clear", handle_clear))
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(CommandHandler(["start", "help"], handle_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot polling — talk to me on Telegram!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

