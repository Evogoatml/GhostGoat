import os
import json
import re
import asyncio
from typing import Tuple
from openai import AsyncOpenAI

client = AsyncOpenAI()

SYSTEM = """You are a pragmatic planner. Decide next best action.
If a tool is needed, choose one from: shell, web_search, read_file, write_file, list_training, train, search_training.
Training tools: list_training (list available ML algorithms), train (run a training algorithm by name), search_training (find training files).
Return JSON with keys: thought, tool, input."""


async def llm(messages):
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3
    )
    return resp.choices[0].message.content


class Planner:
    async def decide(self, task: str, context: list[str]) -> Tuple[str, str, dict]:
        content = await llm([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Task: {task}\nContext:\n" + "\n".join(context)}
        ])
        # naive JSON extraction
        m = re.search(r'\{.*\}', content, re.S)
        obj = json.loads(m.group(0)) if m else {"thought": content, "tool": None, "input": None}
        return obj.get("thought", ""), obj.get("tool"), obj.get("input") or {}

    def done(self, step) -> bool:
        # simple stopping heuristic
        t = (step.thought or "").lower()
        return ("final" in t) or ("complete" in t) or (step.action is None and "no further" in t)
