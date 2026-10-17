"""LLM gateway service: the single provider-backed completion path for every agent."""

import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

OPENAI_COMPATIBLE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "ollama": "http://localhost:11434/v1",
    "local": "http://localhost:11434/v1",
    # Free-tier presets (github.com/mnfst/awesome-free-llm-apis)
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "mistral": "https://api.mistral.ai/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "nim": "https://integrate.api.nvidia.com/v1",
    "ollama-cloud": "https://ollama.com/v1",
    "kilo": "https://api.kilo.ai/api/gateway",
    "ovh": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
}

# Providers that authenticate by IP/anonymous access instead of an API key.
KEYLESS_PROVIDERS = {"ollama", "local", "kilo", "ovh"}

# Generic escape hatch: provider="openai-compatible" + llm.base_url=<any
# OpenAI-compatible endpoint> reaches every other provider on the list above
# without adding it here.
GENERIC_PROVIDER = "openai-compatible"

# Default retry settings for rate limits
MAX_RETRIES = 5
BASE_RETRY_DELAY = 2.0  # seconds
MAX_RETRY_DELAY = 60.0


class LLMGateway:
    """Calls the provider selected in ``config.llm`` (Anthropic, Gemini or OpenAI-compatible)."""

    def __init__(self, llm_config: Any):
        provider = llm_config.provider.value
        if provider == "mock":
            raise RuntimeError("LLM_PROVIDER=mock is not allowed in the full runtime")
        if provider == GENERIC_PROVIDER and not llm_config.base_url:
            raise RuntimeError(f"provider '{GENERIC_PROVIDER}' requires llm.base_url")
        if (provider not in OPENAI_COMPATIBLE_URLS
                and provider not in ("anthropic", "gemini", GENERIC_PROVIDER)):
            raise RuntimeError(f"Unsupported LLM provider: {provider}")
        if (provider not in KEYLESS_PROVIDERS
                and provider != GENERIC_PROVIDER
                and not llm_config.api_key):
            raise RuntimeError(f"API key for LLM provider '{provider}' is not configured")
        self.config = llm_config
        self.provider = provider

    def describe(self) -> Dict[str, Any]:
        return {"provider": self.provider, "model": self.config.model}

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        return await asyncio.to_thread(self._complete_sync, prompt, system)

    def _post_with_retry(self, url: str, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """POST with exponential backoff retry for rate limits (429) and server errors (5xx)."""
        request = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={"content-type": "application/json", **headers},
        )
        
        delay = BASE_RETRY_DELAY
        last_exception = None
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.config.timeout) as response:  # nosec - provider URL from config
                    return json.loads(response.read())
            except urllib.error.HTTPError as e:
                last_exception = e
                # Retry on rate limit (429) or server errors (5xx)
                if e.code == 429 or (500 <= e.code < 600):
                    if attempt < MAX_RETRIES:
                        retry_after = e.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = min(float(retry_after), MAX_RETRY_DELAY)
                        print(f"[LLM Gateway] Rate limited (HTTP {e.code}), retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(delay)
                        delay = min(delay * 2, MAX_RETRY_DELAY)  # exponential backoff
                        continue
                # For other HTTP errors, re-raise immediately
                raise
            except urllib.error.URLError as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    print(f"[LLM Gateway] Network error: {e}, retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    delay = min(delay * 2, MAX_RETRY_DELAY)
                    continue
                raise
        
        # All retries exhausted
        raise RuntimeError(f"LLM request failed after {MAX_RETRIES} retries: {last_exception}")

    def _complete_sync(self, prompt: str, system: Optional[str]) -> str:
        cfg = self.config
        if self.provider == "anthropic":
            data = self._post_with_retry(
                "https://api.anthropic.com/v1/messages",
                {"model": cfg.model, "max_tokens": cfg.max_tokens, "temperature": cfg.temperature,
                 **({"system": system} if system else {}),
                 "messages": [{"role": "user", "content": prompt}]},
                {"x-api-key": cfg.api_key, "anthropic-version": "2023-06-01"},
            )
            return data["content"][0]["text"]
        if self.provider == "gemini":
            data = self._post_with_retry(
                f"https://generativelanguage.googleapis.com/v1beta/models/{cfg.model}:generateContent",
                {**({"systemInstruction": {"parts": [{"text": system}]}} if system else {}),
                 "contents": [{"role": "user", "parts": [{"text": prompt}]}]},
                {"x-goog-api-key": cfg.api_key},
            )
            return data["candidates"][0]["content"]["parts"][0]["text"]
        base = (cfg.base_url or OPENAI_COMPATIBLE_URLS[self.provider]).rstrip("/")
        if self.provider in ("ollama", "local") and not base.endswith("/v1"):
            base += "/v1"
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        data = self._post_with_retry(
            f"{base}/chat/completions",
            {"model": cfg.model, "messages": messages, "max_tokens": cfg.max_tokens,
             "temperature": cfg.temperature},
            {"authorization": "Bearer " + (cfg.api_key or "")},
        )
        return data["choices"][0]["message"]["content"]
