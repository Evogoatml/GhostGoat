"""LLM gateway service: the single provider-backed completion path for every agent."""

import asyncio
import json
import urllib.request
from typing import Any, Dict, Optional

OPENAI_COMPATIBLE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "ollama": "http://localhost:11434/v1",
    "local": "http://localhost:11434/v1",
}


class LLMGateway:
    """Calls the provider selected in ``config.llm`` (Anthropic, Gemini or OpenAI-compatible)."""

    def __init__(self, llm_config: Any):
        provider = llm_config.provider.value
        if provider == "mock":
            raise RuntimeError("LLM_PROVIDER=mock is not allowed in the full runtime")
        if provider not in OPENAI_COMPATIBLE_URLS and provider not in ("anthropic", "gemini"):
            raise RuntimeError(f"Unsupported LLM provider: {provider}")
        if provider not in ("ollama", "local") and not llm_config.api_key:
            raise RuntimeError(f"API key for LLM provider '{provider}' is not configured")
        self.config = llm_config
        self.provider = provider

    def describe(self) -> Dict[str, Any]:
        return {"provider": self.provider, "model": self.config.model}

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        return await asyncio.to_thread(self._complete_sync, prompt, system)

    def _post(self, url: str, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        request = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers={"content-type": "application/json", **headers},
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout) as response:  # nosec - provider URL from config
            return json.loads(response.read())

    def _complete_sync(self, prompt: str, system: Optional[str]) -> str:
        cfg = self.config
        if self.provider == "anthropic":
            data = self._post(
                "https://api.anthropic.com/v1/messages",
                {"model": cfg.model, "max_tokens": cfg.max_tokens, "temperature": cfg.temperature,
                 **({"system": system} if system else {}),
                 "messages": [{"role": "user", "content": prompt}]},
                {"x-api-key": cfg.api_key, "anthropic-version": "2023-06-01"},
            )
            return data["content"][0]["text"]
        if self.provider == "gemini":
            data = self._post(
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
        data = self._post(
            f"{base}/chat/completions",
            {"model": cfg.model, "messages": messages, "max_tokens": cfg.max_tokens,
             "temperature": cfg.temperature},
            {"authorization": "Bearer " + (cfg.api_key or "")},
        )
        return data["choices"][0]["message"]["content"]
