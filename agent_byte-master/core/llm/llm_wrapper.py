"""Unified async LLM wrapper for GhostGoat.

The wrapper picks a provider based on the ``LLM_PROVIDER`` environment variable:
* ``ollama`` – calls the local Ollama server via ``curl``
* ``openai`` – calls the OpenAI chat completions endpoint (requires ``OPENAI_API_KEY``)

It returns the plain text answer and logs latency, token counts and any
errors.  The implementation uses the ``terminal`` tool for HTTP calls – this
avoids pulling in heavy HTTP libraries and works inside the constrained Docker
image.
"""

import os
import json
import logging
import time
from typing import Optional

from hermes_tools import terminal  # provided by the platform

log = logging.getLogger(__name__)

class LLMError(RuntimeError):
    """Raised when the provider returns a non‑200 response or malformed payload."""

async def _call_ollama(model: str, prompt: str) -> str:
    """Query a local Ollama server (default ``http://localhost:11434``)."""
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    cmd = (
        f"curl -s -X POST {base}/api/chat "
        f"-H 'Content-Type: application/json' "
        f"-d '{json.dumps(payload)}'"
    )
    result = await terminal(command=cmd, timeout=30)
    if result["exit_code"] != 0:
        raise LLMError(f"Ollama curl failed: {result['output']}")
    data = json.loads(result["output"])
    return data["message"]["content"]

async def _call_openai(model: str, prompt: str) -> str:
    """Query OpenAI's chat‑completion API (``OPENAI_API_KEY`` required)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY not set")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    cmd = (
        f"curl -s -X POST {base}/v1/chat/completions "
        f"-H 'Content-Type: application/json' "
        f"-H 'Authorization: Bearer {api_key}' "
        f"-d '{json.dumps(payload)}'"
    )
    result = await terminal(command=cmd, timeout=30)
    if result["exit_code"] != 0:
        raise LLMError(f"OpenAI curl failed: {result['output']}")
    data = json.loads(result["output"])
    return data["choices"][0]["message"]["content"]

async def call(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """Public entry‑point.

    Parameters
    ----------
    prompt: str – the user‑augmented prompt that will be sent to the model.
    system_prompt: Optional[str] – a system message; if omitted the wrapper
        does not send an explicit system role (the caller can prepend it).
    provider: Optional[str] – force a provider (``ollama`` or ``openai``).
    """
    start = time.time()
    provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
    model = os.getenv("LLM_MODEL", "llama3.2")

    # If a system_prompt is supplied we prepend it as a separate message for the
    # providers that support multi‑message payloads.
    if system_prompt:
        # For Ollama we can include it directly in the ``messages`` list – the
        # existing ``_call_ollama`` implementation only sends a single user
        # message, so we embed it into the prompt text.
        prompt = f"{system_prompt}\n\n{prompt}"

    try:
        if provider == "ollama":
            answer = await _call_ollama(model, prompt)
        elif provider == "openai":
            answer = await _call_openai(model, prompt)
        else:
            raise LLMError(f"Unsupported provider: {provider}")
    except Exception as exc:
        log.exception("LLM call failed")
        raise
    finally:
        latency = time.time() - start
        log.info(
            "LLM request completed",
            extra={"provider": provider, "model": model, "latency_s": latency},
        )
    return answer
