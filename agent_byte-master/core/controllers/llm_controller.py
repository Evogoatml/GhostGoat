"""
LLMController — unified LLM routing for all agents.

Priority order (local-first, API fallback):
  1. Ollama  (local, zero cost)  — requires `ollama serve` running
  2. HuggingFace pipeline (local, CPU/GPU)
  3. Anthropic Claude (API)
  4. OpenAI GPT-4o (API)
  5. Google Gemini (API)
  6. Echo stub (last resort)
"""
from __future__ import annotations
import logging
import os
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Default local model — small, fast, runs on CPU
_DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
_DEFAULT_HF_MODEL = os.getenv("HF_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
_OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
_OLLAMA_CLOUD_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")


class LLMController:
    """Single LLM interface. Local-first, API fallback."""

    _instance: Optional["LLMController"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
            cls._instance._providers = []
            cls._instance._provider_names = []
        return cls._instance

    def __init__(self):
        if self._ready:
            return
        self._build_providers()
        self._ready = True

    # ── provider registration ─────────────────────────────────────────────────

    def _build_providers(self):
        """Build the list of LLM providers in priority order."""
        # 0. Ollama Cloud - for cloud models like gpt-oss:120b-cloud
        self._try_register_ollama_cloud()

        # 1. Ollama local server
        self._try_register_ollama()

        # 2. HuggingFace
        self._try_register_hf()

        # 3. Anthropic
        self._try_register_anthropic()

        # 4. OpenAI
        self._try_register_openai()

        # 5. Gemini
        self._try_register_gemini()

        if not self._providers:
            logger.warning("[LLM] No providers available — using echo stub")
            self._providers.append(lambda p: f"[LLM stub] {p[:200]}")
            self._provider_names.append("echo-stub")
        else:
            logger.info("[LLM] Active providers: %s", self._provider_names)

    # ── provider registration ─────────────────────────────────────────────────

    def _try_register_ollama_cloud(self):
        """Try Ollama Cloud with API key - supports cloud models like gpt-oss:120b-cloud."""
        api_key = os.getenv("OLLAMA_API_KEY", "")
        if not api_key or "your-" in api_key.lower():
            logger.debug("[LLM] OLLAMA_API_KEY not set, skipping Ollama Cloud")
            return
        
        try:
            from openai import OpenAI
            model = os.getenv("LLM_MODEL", "gpt-oss:120b-cloud")
            base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
            
            client = OpenAI(
                base_url=f"{base_url}/v1",
                api_key=api_key,
            )
            
            def _ollama_cloud(prompt: str, system: str = "", _client=client, _model=model) -> str:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                resp = _client.chat.completions.create(
                    model=_model,
                    messages=messages,
                )
                return resp.choices[0].message.content
            
            self._providers.append(_ollama_cloud)
            self._provider_names.append(f"ollama-cloud:{model}")
            logger.info("[LLM] Ollama Cloud registered (model=%s, base_url=%s)", model, base_url)
        except Exception as e:
            logger.debug("[LLM] Ollama Cloud unavailable: %s", e)

    def _try_register_ollama(self):
        """Try Ollama local server via REST or SDK."""
        try:
            import requests  # always available
            resp = requests.get(f"{_OLLAMA_HOST}/api/tags", timeout=2)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                model = _DEFAULT_OLLAMA_MODEL
                # pick first available model if default not present
                if models and not any(model in m for m in models):
                    model = models[0].split(":")[0]
                    logger.info("[LLM] Ollama default '%s' not found, using '%s'", _DEFAULT_OLLAMA_MODEL, model)

                def _ollama(prompt: str, system: str = "", _model=model) -> str:
                    body: dict = {"model": _model, "prompt": prompt, "stream": False}
                    if system:
                        body["system"] = system
                    r = requests.post(
                        f"{_OLLAMA_HOST}/api/generate",
                        json=body,
                        timeout=120,
                    )
                    r.raise_for_status()
                    return r.json()["response"]

                self._providers.append(_ollama)
                self._provider_names.append(f"ollama:{model}")
                logger.info("[LLM] Ollama registered (model=%s, host=%s)", model, _OLLAMA_HOST)
                return
        except Exception as e:
            logger.debug("[LLM] Ollama not available: %s", e)

        # Fallback: try official ollama Python client
        try:
            import ollama as ollama_client
            model = _DEFAULT_OLLAMA_MODEL

            def _ollama_sdk(prompt: str, _m=model) -> str:
                resp = ollama_client.generate(model=_m, prompt=prompt)
                return resp["response"]

            # Quick liveness check
            ollama_client.list()
            self._providers.append(_ollama_sdk)
            self._provider_names.append(f"ollama-sdk:{model}")
            logger.info("[LLM] Ollama SDK registered (model=%s)", model)
        except Exception as e:
            logger.debug("[LLM] Ollama SDK not available: %s", e)

    def _try_register_hf(self):
        """Try HuggingFace local pipeline — CPU-safe, quantised."""
        hf_model = os.getenv("HF_MODEL", "")
        if not hf_model:
            logger.debug("[LLM] HF_MODEL not set, skipping local HF pipeline")
            return
        try:
            from transformers import pipeline as hf_pipeline
            import torch

            device = 0 if torch.cuda.is_available() else -1
            pipe = hf_pipeline(
                "text-generation",
                model=hf_model,
                device=device,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.7,
            )

            def _hf(prompt: str, _p=pipe) -> str:
                out = _p(prompt, max_new_tokens=512, return_full_text=False)
                return out[0]["generated_text"].strip()

            self._providers.append(_hf)
            self._provider_names.append(f"hf:{hf_model}")
            logger.info("[LLM] HuggingFace pipeline registered (model=%s, device=%s)", hf_model, device)
        except Exception as e:
            logger.debug("[LLM] HuggingFace pipeline unavailable: %s", e)

    def _try_register_anthropic(self):
        try:
            import anthropic
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if key and "placeholder" not in key.lower():
                _ac = anthropic.Anthropic(api_key=key)

                def _anthropic(prompt: str, system: str = "", _c=_ac) -> str:
                    kwargs = dict(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4096,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    if system:
                        kwargs["system"] = system
                    msg = _c.messages.create(**kwargs)
                    return msg.content[0].text

                self._providers.append(_anthropic)
                self._provider_names.append("anthropic:claude-sonnet-4")
                logger.info("[LLM] Anthropic registered")
        except Exception as e:
            logger.debug("[LLM] Anthropic unavailable: %s", e)

    def _try_register_openai(self):
        try:
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY", "")
            if key and "your-" not in key.lower() and "placeholder" not in key.lower():
                _oc = OpenAI(api_key=key)

                def _openai(prompt: str, system: str = "", _c=_oc) -> str:
                    messages = []
                    if system:
                        messages.append({"role": "system", "content": system})
                    messages.append({"role": "user", "content": prompt})
                    resp = _c.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                    )
                    return resp.choices[0].message.content

                self._providers.append(_openai)
                self._provider_names.append("openai:gpt-4o")
                logger.info("[LLM] OpenAI registered")
        except Exception as e:
            logger.debug("[LLM] OpenAI unavailable: %s", e)

    def _try_register_gemini(self):
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            return
        # Try new google-genai SDK first, fall back to deprecated google-generativeai
        try:
            from google import genai as new_genai
            client = new_genai.Client(api_key=key)

            def _gemini_new(prompt: str, system: str = "", _c=client) -> str:
                contents = (system + "\n\n" + prompt) if system else prompt
                resp = _c.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=contents,
                )
                return resp.text

            self._providers.append(_gemini_new)
            self._provider_names.append("gemini:gemini-2.0-flash")
            logger.info("[LLM] Gemini (google-genai) registered")
        except Exception:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    import google.generativeai as genai
                genai.configure(api_key=key)
                _gm = genai.GenerativeModel("gemini-1.5-pro")

                def _gemini(prompt: str, system: str = "", _m=_gm) -> str:
                    contents = (system + "\n\n" + prompt) if system else prompt
                    return _m.generate_content(contents).text

                self._providers.append(_gemini)
                self._provider_names.append("gemini:gemini-1.5-pro")
                logger.info("[LLM] Gemini (google-generativeai) registered")
            except Exception as e:
                logger.debug("[LLM] Gemini unavailable: %s", e)

    def search(self, query: str) -> str:
        """Search the web using Ollama Cloud."""
        try:
            from openai import OpenAI
            api_key = os.getenv("OLLAMA_API_KEY") or os.getenv("OLLAMA_API_KEY")
            base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
            if not api_key:
                return "Set OLLAMA_API_KEY in .env"
            client = OpenAI(api_key=api_key, base_url=f"{base_url}/v1")
            resp = client.chat.completions.create(
                model="gpt-oss:120b-cloud",
                messages=[
                    {"role": "system", "content": "You are a web search assistant. Return 3 results with title, URL, summary."},
                    {"role": "user", "content": f"Web search for: {query}"}
                ],
                temperature=0.3, max_tokens=1500,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"Search error: {e}"

    # ── public API ────────────────────────────────────────────────────────────

    def call(self, prompt: str, system: str = "") -> str:
        """Call the best available LLM. Falls back through providers on error."""
        for i, provider in enumerate(self._providers):
            try:
                import inspect
                sig = inspect.signature(provider)
                if "system" in sig.parameters:
                    return provider(prompt, system=system)
                return provider(prompt)
            except Exception as e:
                name = self._provider_names[i] if i < len(self._provider_names) else f"provider-{i}"
                logger.warning("[LLM] %s failed, trying next: %s", name, e)
        return "[LLM] all providers failed"

    def active_provider(self) -> str:
        """Return the name of the currently primary provider."""
        return self._provider_names[0] if self._provider_names else "none"

    def as_callable(self) -> Callable[[str], str]:
        """Return self.call as a plain callable (for PMMAGO tiles)."""
        return self.call


# Singleton - created lazily
_llm_instance = None

def get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMController()
    return _llm_instance

llm = get_llm()
