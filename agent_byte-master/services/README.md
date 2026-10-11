# Runtime services

Every module here is registered by the orchestrator (`run_cognitive_system.py`) at
startup and shares its state.

| Service | Registry name | Purpose |
|---|---|---|
| `llm_gateway.py` | `llm` | Single provider-backed completion path (Anthropic, Gemini, OpenAI, DeepSeek, Ollama) configured from `config/unified_config.py`. A missing key or `LLM_PROVIDER=mock` fails boot. |
| `sentiment_service.py` | `sentiment` | CryptoBERT sentiment; also the `sentiment-1` agent. Weights load on first use. |
| `telegram_bot.py` | `telegram` | Telegram transport for the orchestrator. |

## Telegram (`telegram_bot.py`)

Environment (see `TelegramConfig` in `config/unified_config.py`):

- `TELEGRAM_BOT_TOKEN` - bot token; the transport (long polling, or webhook when
  `TELEGRAM_WEBHOOK_URL` is set) connects with it. Without a token the service is
  still registered and `POST /api/telegram/webhook` still answers through the
  orchestrator, but nothing is sent to Telegram.
- `TELEGRAM_CHAT_ID` - allowed chat IDs, comma-separated. Other chats are ignored.
- `TELEGRAM_WEBHOOK_SECRET` - checked against `X-Telegram-Bot-Api-Secret-Token`.

Flow: Telegram -> `TelegramBotService` -> `orchestrator.process_goal()` -> reply.
Commands: `/status`, `/agents`, `/memory`, `/history`, `/help`. Task, memory and
graph events from the orchestrator (including API tasks) are pushed to the chats.
