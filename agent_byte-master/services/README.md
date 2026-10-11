# Optional services

This directory contains specialized Agent Byte services outside the supported
GhostGoat runtime. `sentiment_service.py` provides optional crypto sentiment
analysis and is not imported by the core API.

## Telegram bot (`telegram_bot.py`)

Optional service that lets you drive the real orchestrator from Telegram. It
only starts when `TELEGRAM_BOT_TOKEN` is set.

### Setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Set the environment (see `config/unified_config.py`, `TelegramConfig`):
   - `TELEGRAM_BOT_TOKEN` – bot token (required to enable the bot).
   - `TELEGRAM_CHAT_ID` – allowed chat/group IDs, comma-separated
     (e.g. `12345,-100987654`). Messages from other chats are ignored, and if
     empty nobody can send goals.
   - `TELEGRAM_WEBHOOK_URL` – optional public URL of `/api/telegram/webhook`.
     If unset the bot uses long polling.
   - `TELEGRAM_WEBHOOK_SECRET` – optional secret checked against the
     `X-Telegram-Bot-Api-Secret-Token` header.
3. Run `python main.py`. The bot runs inside the API process and shuts down
   with it.

### Message flow

```
Telegram → /api/telegram/webhook (or polling) → TelegramBotService
        → orchestrator process_goal() (agent network) → response → Telegram sendMessage
```

Any plain text is a goal. Commands: `/status`, `/agents`, `/memory`,
`/history`, `/help`. Tasks submitted through `POST /api/tasks` are also
broadcast to the configured chats. Conversation history is tracked per chat.
