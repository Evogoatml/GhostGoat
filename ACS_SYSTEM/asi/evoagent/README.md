# EvoAgent MVP
- ReAct loop with tool use
- SQLite + embeddings memory
- Task runner & run logs

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip uv || true
pip install -e .
cp .env.example .env && edit keys
python -m agent.main "Draft a 3-bullet brief on FAISS best practices"
```
