"""Free-tier LLM providers: presets, generic openai-compatible escape hatch, keyless access."""

import pytest

from config.unified_config import LLMConfig, LLMProvider
from services.llm_gateway import (
    GENERIC_PROVIDER,
    KEYLESS_PROVIDERS,
    OPENAI_COMPATIBLE_URLS,
    LLMGateway,
)

PRESETS = ["groq", "openrouter", "mistral", "zhipu", "nim", "ollama-cloud"]


def test_presets_are_in_gateway_map():
    for preset in PRESETS:
        assert preset in OPENAI_COMPATIBLE_URLS
        assert LLMProvider(preset).value == preset  # enum accepts env string


def test_each_preset_constructs_a_gateway():
    for preset in PRESETS:
        cfg = LLMConfig(provider=LLMProvider(preset), model="test-model", api_key="k")
        gw = LLMGateway(cfg)
        assert gw.provider == preset


@pytest.mark.parametrize("provider", sorted(KEYLESS_PROVIDERS - {"local", "ollama"}))
def test_keyless_providers_need_no_api_key(provider):
    cfg = LLMConfig(provider=LLMProvider(provider), model="test-model", api_key=None)
    assert LLMGateway(cfg).provider == provider


def test_keyed_preset_still_requires_key():
    cfg = LLMConfig(provider=LLMProvider.GROQ, model="m", api_key=None)
    with pytest.raises(RuntimeError, match="API key"):
        LLMGateway(cfg)


def test_generic_provider_requires_base_url():
    cfg = LLMConfig(provider=LLMProvider.OPENAI_COMPATIBLE, model="m", api_key=None)
    with pytest.raises(RuntimeError, match="base_url"):
        LLMGateway(cfg)


def test_generic_provider_is_keyless_allowed():
    cfg = LLMConfig(
        provider=LLMProvider.OPENAI_COMPATIBLE, model="m",
        base_url="https://anonymous.endpoint.example/v1",
    )
    assert LLMGateway(cfg).provider == GENERIC_PROVIDER


def _capture_post(gw, monkeypatch):
    captured = {}

    def fake_post(url, body, headers):
        captured["url"] = url
        captured["model"] = body.get("model")
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(gw, "_post_with_retry", fake_post)
    return captured


def test_groq_request_url_and_auth(monkeypatch):
    gw = LLMGateway(LLMConfig(provider=LLMProvider.GROQ, model="openai/gpt-oss-120b", api_key="k"))
    captured = _capture_post(gw, monkeypatch)
    assert gw._complete_sync("hi", None) == "ok"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["model"] == "openai/gpt-oss-120b"


def test_generic_provider_uses_base_url(monkeypatch):
    gw = LLMGateway(LLMConfig(
        provider=LLMProvider.OPENAI_COMPATIBLE, model="free-model",
        base_url="https://my.free.endpoint/v1",
    ))
    captured = _capture_post(gw, monkeypatch)
    assert gw._complete_sync("hi", None) == "ok"
    assert captured["url"] == "https://my.free.endpoint/v1/chat/completions"


def test_from_env_preset(monkeypatch):
    from config.unified_config import UnifiedConfig  # noqa: F401  (ensures module fully loads)

    for var in ("LLM_MODEL", "LLM_BASE_URL", "GROQ_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_API_KEY", "env-key")
    cfg = LLMConfig.from_env()
    assert cfg.provider == LLMProvider.GROQ
    assert cfg.base_url == "https://api.groq.com/openai/v1"
    assert cfg.api_key == "env-key"
    assert cfg.model == "openai/gpt-oss-120b"  # preset default model


def test_from_env_generic_provider(monkeypatch):
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_BASE_URL", "https://some.other.free.host/v1")
    monkeypatch.setenv("LLM_API_KEY", "env-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = LLMConfig.from_env()
    assert cfg.provider == LLMProvider.OPENAI_COMPATIBLE
    assert cfg.base_url == "https://some.other.free.host/v1"
    gw = LLMGateway(cfg)  # constructs without error
    assert gw.provider == GENERIC_PROVIDER


def test_unknown_provider_still_rejected():
    cfg = LLMConfig(provider=LLMProvider.MOCK, model="m", api_key=None)
    with pytest.raises(RuntimeError, match="mock"):
        LLMGateway(cfg)


def test_validate_accepts_keyless_but_requires_key_for_keyed_providers(monkeypatch):
    from config.unified_config import UnifiedConfig

    monkeypatch.setenv("LLM_PROVIDER", "ovh")
    for var in ("LLM_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    cfg = UnifiedConfig.from_env()
    is_valid, errors = cfg.validate()
    assert is_valid, errors  # keyless provider needs no API key

    monkeypatch.setenv("LLM_PROVIDER", "groq")
    cfg = UnifiedConfig.from_env()
    is_valid, errors = cfg.validate()
    assert not is_valid
    assert any("API key" in e for e in errors)
