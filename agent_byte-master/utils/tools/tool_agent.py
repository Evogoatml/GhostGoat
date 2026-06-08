"""
GhostGoat Tool Agent — ReAct loop that gives the LLM real abilities.

The LLM can call any registered tool by writing:
    ACTION: tool_name
    INPUT: {"key": "value"}

The agent runs up to MAX_STEPS iterations, feeding tool results back to the
LLM until it writes FINAL ANSWER: ... or runs out of steps.
"""

from __future__ import annotations
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_STEPS = 6

SYSTEM_PROMPT = """\
You are GhostGoat 🐐, a highly capable personal AI partner. Your job is to help the user \
bring their ideas to life — building software, researching topics, creating content, running \
analysis, writing scripts, and anything else they need.

You have access to real tools. To use a tool, write exactly:
ACTION: <tool_name>
INPUT: <json object with parameters>

Then STOP — the system will run the tool and give you the result as:
OBSERVATION: <result>

After seeing the result you can call more tools or write your final answer:
FINAL ANSWER: <your complete answer to the user>

Available tools:
- web_search(query, max_results=6) — search the web via DuckDuckGo
- fetch_url(url) — download and read a webpage
- execute_python(code, timeout=15) — run Python code, returns stdout/stderr
- create_workspace_file(filename, content) — save a file to ~/ghostgoat_workspace/
- list_directory(path) — list files in a directory
- read_file(path) — read a file
- write_file(path, content) — write a file at an absolute path
- remember(key, value) — store something permanently in memory
- recall(key="") — retrieve memories (empty key = list all)
- system_info() — get CPU/memory/platform info
- http_request(url, method="GET") — make an HTTP request
- set_api_key(service, key) — save an API key to .env and activate it instantly
  (services: openai, anthropic, google, gemini, huggingface, telegram, groq, mistral, etc.)
- list_api_keys() — show which keys are configured
- search_hf_models(query, task="", limit=8) — find HuggingFace models (task: text-generation, image-classification, etc.)
- search_hf_datasets(query, limit=8) — find HuggingFace datasets
- get_hf_model_info(model_id) — detailed info on a specific HF model
- download_hf_model(model_id, cache_dir="") — download/cache a HF model locally
- search_github(query, language="", sort="stars", limit=8) — search GitHub repos
- clone_github_repo(url, dest="", branch="") — clone a repo to ~/ghostgoat_workspace/
- install_package(package) — pip install any package
- install_requirements(repo_path) — pip install -r requirements.txt from a cloned repo

Rules:
1. Always use tools when you need real information or need to produce real outputs.
2. For code tasks: write the code, execute it, show the user the result.
3. For research: search the web and synthesise findings — don't make things up.
4. Be decisive. Do things rather than describing what you could do.
5. Keep answers focused and practical.
6. If you build something, save it with create_workspace_file and tell the user where to find it.
7. If the user sends an API key (anything starting with sk-, AIza, hf_, or a long alphanumeric string after mentioning a service), use set_api_key immediately so GhostGoat can use that service.
8. After saving an API key, confirm it's active and explain what GhostGoat can now do with it.
9. When a task needs a model or library you don't have: search HuggingFace or GitHub, pick the best one, install it, and use it — all in one flow.
10. When cloning a repo: always run install_requirements afterward so it's ready to use.
"""


class ToolAgent:
    """Stateless ReAct agent. Each call() is independent."""

    def __init__(self):
        from core.controllers.llm_controller import llm
        from tools.registry import registry
        self._llm = llm
        self._registry = registry

    def call(
        self,
        user_message: str,
        history: Optional[List[str]] = None,
        username: str = "friend",
        user_id: str = "default",
    ) -> str:
        """Run the ReAct loop and return the final text response."""
        from core.memory.conversation_memory import conversation_memory
        from core.memory.trace_logger import trace_logger

        # Store the incoming user message
        conversation_memory.store(user_id, "user", user_message)

        # Run background compression if memory is getting large
        try:
            conversation_memory.compress_if_needed(user_id, self._llm.call)
        except Exception:
            pass

        # Retrieve semantically relevant past context
        relevant_memories = conversation_memory.retrieve(user_id, user_message)

        # Build context block: memories first, then recent turns
        context_parts = []
        if relevant_memories:
            context_parts.append(
                "Relevant past context:\n" + "\n".join(f"  {m}" for m in relevant_memories)
            )
        if history:
            context_parts.append(
                "Recent conversation:\n" + "\n".join(f"  {h}" for h in history[-4:])
            )
        context_block = ("\n\n".join(context_parts) + "\n\n") if context_parts else ""

        # Build initial prompt (system prompt sent separately so API providers
        # receive it via the system role, not mixed into user content)
        prompt = (
            f"{context_block}"
            + f"User ({username}): {user_message}\n\nThought:"
        )

        scratchpad: List[str] = []
        last_raw = ""

        for step in range(MAX_STEPS):
            try:
                raw = self._llm.call(prompt + "".join(scratchpad), system=SYSTEM_PROMPT)
            except Exception as e:
                logger.warning("[ToolAgent] LLM call failed at step %d: %s", step, e)
                raw = f"FINAL ANSWER: I hit an LLM error: {e}. Please check your API key."

            last_raw = raw

            # Check for FINAL ANSWER first
            if "FINAL ANSWER:" in raw:
                answer = raw.split("FINAL ANSWER:", 1)[1].strip()
                conversation_memory.store(user_id, "assistant", answer)
                # Log trace only when tools were actually used
                if scratchpad:
                    trace_logger.log(
                        user_id=user_id,
                        system_prompt=SYSTEM_PROMPT,
                        user_message=user_message,
                        scratchpad=scratchpad,
                        final_answer=answer,
                        quality="good",
                    )
                return answer

            # Check for ACTION/INPUT block
            action_match = re.search(
                r"ACTION:\s*(\w+)\s*\nINPUT:\s*(\{.*?\})",
                raw, re.S
            )
            if not action_match:
                # No tool call and no FINAL ANSWER — the LLM answered directly.
                # Remove ReAct prefixes from the start of lines only, keep content.
                lines = raw.splitlines()
                cleaned = [
                    l for l in lines
                    if not re.match(r"^(Thought:|ACTION:|INPUT:|OBSERVATION:)\s*$", l.strip())
                ]
                answer = "\n".join(cleaned).strip() or raw.strip()
                conversation_memory.store(user_id, "assistant", answer)
                return answer

            tool_name = action_match.group(1).strip()
            try:
                tool_input: Dict[str, Any] = json.loads(action_match.group(2))
            except json.JSONDecodeError:
                tool_input = {}

            # Run the tool
            observation = self._run_tool(tool_name, tool_input)

            # Append to scratchpad so next iteration has full context
            scratchpad.append(
                f"\nACTION: {tool_name}\nINPUT: {json.dumps(tool_input)}"
                f"\nOBSERVATION: {observation}\nThought:"
            )

            logger.info("[ToolAgent] step=%d tool=%s obs_len=%d", step + 1, tool_name, len(str(observation)))

        # Ran out of steps — ask LLM to wrap up
        try:
            final_prompt = (
                prompt
                + "".join(scratchpad)
                + "\nYou have reached the step limit. Summarise what you found and give a final answer.\nFINAL ANSWER:"
            )
            answer = self._llm.call(final_prompt, system=SYSTEM_PROMPT)
            if "FINAL ANSWER:" in answer:
                answer = answer.split("FINAL ANSWER:", 1)[1].strip()
            else:
                answer = answer.strip()
        except Exception as e:
            # Absolute last resort: return whatever the last raw LLM output was
            answer = last_raw.strip() or f"I ran out of steps and hit an error: {e}"
        conversation_memory.store(user_id, "assistant", answer)
        if scratchpad:
            trace_logger.log(
                user_id=user_id,
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                scratchpad=scratchpad,
                final_answer=answer,
                quality="partial",
            )
        return answer

    def _run_tool(self, name: str, params: Dict[str, Any]) -> str:
        result = self._registry.execute_tool(name, **params)
        if result.success:
            out = result.output
            if isinstance(out, (dict, list)):
                text = json.dumps(out, indent=2)
            else:
                text = str(out)
            # Truncate very long results
            return text[:3000] + (" ... [truncated]" if len(text) > 3000 else "")
        return f"ERROR: {result.error}"


# Singleton
_agent: Optional[ToolAgent] = None


def get_tool_agent() -> ToolAgent:
    global _agent
    if _agent is None:
        _agent = ToolAgent()
    return _agent
