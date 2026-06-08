# GhostGoat Cheat Sheet 🐐

## Telegram Bot — What to Say

### Setup & Configuration
```
"My OpenAI key is sk-..."
"Set my Anthropic API key: sk-ant-..."
"Here's my HuggingFace token: hf_..."
"Set my Groq key: gsk_..."
"Set my Gemini key: AIza..."
"Show me what API keys are configured"
```

### Build Things
```
"Build me a Python script that [does X]"
"Create a Flask app with [these features]"
"Write a web scraper for [site]"
"Make a Discord bot that [does X]"
"Build a CLI tool that [does X]"
"Set up a project structure for [idea]"
```

### Research & Search
```
"Search for [topic] and summarise"
"What's the latest on [topic]?"
"Find me the best [library/tool] for [task]"
"Research [topic] and give me a report"
"What are people saying about [topic]?"
```

### Run Code
```
"Run this code: [paste code]"
"Calculate [math problem] in Python"
"Parse this data: [data]"
"Test if this code works: [code]"
```

### Create & Save Files
```
"Save this as a file: [content]"
"Create a config file for [service]"
"Write a requirements.txt for [project]"
"Generate a README for [project]"
```
> Files are saved to `~/ghostgoat_workspace/`

### Memory
```
"Remember that my project is [name]"
"Remember my stack is Python + FastAPI"
"Recall everything you know about me"
"Recall my project name"
"How much memory are you using?"
"Show my memory stats"
/clear   ← wipes both short-term history AND long-term semantic memory
```
> Every conversation is stored as a vector in ChromaDB (~/.ghostgoat_chroma/).
> When entries exceed 300, old ones are auto-compressed into daily summaries.

### HuggingFace & GitHub
```
"Find me a model for [task] on HuggingFace"
"Search HuggingFace for text-to-image models"
"Find a dataset for [topic]"
"What's the most popular [language] repo on GitHub for [task]?"
"Clone [github url] and set it up"
"Install the requirements for [repo path]"
"Find and install a library for [task]"
```

### Posters / Images
```
POST /api/poster/generate
{
  "platform": "Instagram",     ← Instagram | LinkedIn | Twitter | YouTube
  "tone": "professional",      ← professional | casual | energetic | fun | witty
  "input_text": "Your idea",
  "logo_base64": null
}
```

---

## API Endpoints (port 8420)

| Method | Endpoint | What it does |
|--------|----------|--------------|
| GET | `/api/health` | System status + which modules loaded |
| GET | `/api/system/metrics` | CPU, memory, disk |
| GET | `/api/agents` | All active agents |
| POST | `/api/tasks` | Submit a task `{"description": "..."}` |
| GET | `/api/tasks` | Task history |
| POST | `/api/poster/generate` | Generate a social media poster |
| GET | `/api/posters/download/{filename}` | Download a generated poster |
| GET | `/api/tools` | List available tools |
| POST | `/api/tools/execute?name=web_search` | Run a tool directly |
| GET | `/api/knowledge/search?q=topic` | Search knowledge base |
| GET | `/api/messages` | Inter-agent message log |
| GET | `/api/governance/policies` | Active governance policies |

---

## Available Tools (used automatically)

| Tool | What it does |
|------|-------------|
| `web_search` | DuckDuckGo search — no API key needed |
| `fetch_url` | Download and read any webpage |
| `execute_python` | Run Python code in a sandbox |
| `create_workspace_file` | Save a file to `~/ghostgoat_workspace/` |
| `read_file` / `write_file` | Read or write any file by path |
| `list_directory` | List files in a folder |
| `remember` | Store a key/value permanently |
| `recall` | Get stored memories |
| `set_api_key` | Save an API key and activate it now |
| `list_api_keys` | See what keys are configured |
| `search_hf_models` | Search HuggingFace for models by task/keyword |
| `search_hf_datasets` | Search HuggingFace for datasets |
| `get_hf_model_info` | Detailed info on a specific HF model |
| `download_hf_model` | Download/cache a HF model locally |
| `search_github` | Search GitHub repos by keyword/language |
| `clone_github_repo` | Clone a repo to `~/ghostgoat_workspace/` |
| `install_package` | `pip install` any package |
| `install_requirements` | Install a repo's `requirements.txt` |
| `system_info` | CPU, memory, platform details |
| `http_request` | Make any HTTP request |
| `port_scan` | Check open ports on a host |

---

## Supported API Services

| What you say | Env var it sets |
|-------------|-----------------|
| openai | `OPENAI_API_KEY` |
| anthropic | `ANTHROPIC_API_KEY` |
| google / gemini | `GOOGLE_API_KEY` / `GEMINI_API_KEY` |
| huggingface / hf | `HUGGINGFACE_API_TOKEN` |
| telegram | `TELEGRAM_BOT_TOKEN` |
| groq | `GROQ_API_KEY` |
| mistral | `MISTRAL_API_KEY` |
| cohere | `COHERE_API_KEY` |
| elevenlabs | `ELEVENLABS_API_KEY` |
| stability | `STABILITY_API_KEY` |
| replicate | `REPLICATE_API_TOKEN` |
| serpapi | `SERP_API_KEY` |

---

## Start / Stop

```bash
# Start everything (API + Dashboard + Telegram bot)
python main.py

# API only
python main.py --api-only

# Dashboard only
python main.py --dash-only

# No Telegram bot
python main.py --no-telegram
```

## Ports
| Service | Port |
|---------|------|
| API | 8420 |
| Dashboard | 3000 |
| AgentBus WebSocket | 8765 |

## Key Directories
| Path | Purpose |
|------|---------|
| `~/ghostgoat_workspace/` | Files GhostGoat creates for you |
| `~/.ghostgoat_memory.json` | Persistent memory store |
| `/home/user/GhostGoat/.env` | API keys and config |
| `core/tool_agent.py` | ReAct agent brain |
| `tools/registry.py` | All tool implementations |
| `core/system.py` | System bootstrapper |
