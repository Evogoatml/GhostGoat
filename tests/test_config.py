"""
Unit tests for config/unified_config.py
"""

import json
import os
import pytest


def _reset():
    """Clear cached global config between tests."""
    import config.unified_config as uc
    uc._config = None


@pytest.fixture(autouse=True)
def clean_config_state():
    _reset()
    yield
    _reset()


# ---------------------------------------------------------------------------
# LLMConfig
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLLMConfig:

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        from config.unified_config import LLMConfig, LLMProvider
        cfg = LLMConfig.from_env()
        assert cfg.provider == LLMProvider.OPENAI
        assert cfg.model == "gpt-4"

    def test_from_env_mock_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        from config.unified_config import LLMConfig, LLMProvider
        cfg = LLMConfig.from_env()
        assert cfg.provider == LLMProvider.MOCK

    def test_from_env_unknown_provider_falls_back_to_openai(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "nonexistent_provider")
        from config.unified_config import LLMConfig, LLMProvider
        cfg = LLMConfig.from_env()
        assert cfg.provider == LLMProvider.OPENAI

    def test_from_env_temperature_parsed(self, monkeypatch):
        monkeypatch.setenv("LLM_TEMPERATURE", "0.3")
        from config.unified_config import LLMConfig
        cfg = LLMConfig.from_env()
        assert cfg.temperature == pytest.approx(0.3)

    def test_from_env_max_tokens_parsed(self, monkeypatch):
        monkeypatch.setenv("LLM_MAX_TOKENS", "500")
        from config.unified_config import LLMConfig
        cfg = LLMConfig.from_env()
        assert cfg.max_tokens == 500


# ---------------------------------------------------------------------------
# MemoryConfig
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMemoryConfig:

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("MEMORY_BACKEND", raising=False)
        from config.unified_config import MemoryConfig, MemoryBackend
        cfg = MemoryConfig.from_env()
        assert cfg.backend == MemoryBackend.CHROMADB

    def test_from_env_memory_backend(self, monkeypatch):
        monkeypatch.setenv("MEMORY_BACKEND", "memory")
        from config.unified_config import MemoryConfig, MemoryBackend
        cfg = MemoryConfig.from_env()
        assert cfg.backend == MemoryBackend.MEMORY

    def test_from_env_unknown_backend_falls_back_to_chromadb(self, monkeypatch):
        monkeypatch.setenv("MEMORY_BACKEND", "unknown_backend")
        from config.unified_config import MemoryConfig, MemoryBackend
        cfg = MemoryConfig.from_env()
        assert cfg.backend == MemoryBackend.CHROMADB


# ---------------------------------------------------------------------------
# UnifiedConfig
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUnifiedConfig:

    def test_to_dict_returns_dict(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.setenv("MEMORY_BACKEND", "memory")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "llm" in d
        assert "memory" in d

    def test_to_dict_serialises_enums_to_strings(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.setenv("MEMORY_BACKEND", "memory")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        d = cfg.to_dict()
        assert isinstance(d["llm"]["provider"], str)
        assert isinstance(d["memory"]["backend"], str)

    def test_validate_mock_provider_no_key_required(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.setenv("MEMORY_BACKEND", "memory")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        cfg.llm.api_key = None
        is_valid, errors = cfg.validate()
        # Mock provider should not require an API key
        api_errors = [e for e in errors if "API key" in e]
        assert api_errors == []

    def test_validate_non_mock_without_key_reports_error(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        cfg.llm.api_key = None
        is_valid, errors = cfg.validate()
        assert not is_valid
        assert any("API key" in e for e in errors)

    def test_save_and_load_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.setenv("MEMORY_BACKEND", "memory")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        cfg_file = str(tmp_path / "config.json")
        cfg.save(cfg_file)

        assert os.path.exists(cfg_file)

        with open(cfg_file) as f:
            data = json.load(f)
        assert data["llm"]["provider"] == "mock"

    def test_save_redacts_api_key(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        cfg.llm.api_key = "super-secret-key"
        cfg_file = str(tmp_path / "config.json")
        cfg.save(cfg_file)

        with open(cfg_file) as f:
            data = json.load(f)
        assert data["llm"]["api_key"] != "super-secret-key"
        assert "REDACTED" in data["llm"]["api_key"]

    def test_load_from_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.setenv("MEMORY_BACKEND", "memory")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        cfg_file = str(tmp_path / "config.json")
        cfg.save(cfg_file)

        loaded = UnifiedConfig.load(cfg_file)
        assert loaded is not None
        assert loaded.to_dict()["llm"]["provider"] == "mock"

    def test_get_system_config_orchestrator(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        sys_cfg = cfg.get_system_config("orchestrator")
        assert isinstance(sys_cfg, dict)
        assert "llm" in sys_cfg

    def test_get_system_config_unknown_returns_empty(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        from config.unified_config import UnifiedConfig
        cfg = UnifiedConfig.from_env()
        sys_cfg = cfg.get_system_config("does_not_exist")
        assert sys_cfg == {}

    def test_from_dict_round_trip(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "mock")
        monkeypatch.setenv("MEMORY_BACKEND", "memory")
        from config.unified_config import UnifiedConfig
        original = UnifiedConfig.from_env()
        d = original.to_dict()
        restored = UnifiedConfig.from_dict(d)
        assert restored.to_dict()["llm"]["provider"] == d["llm"]["provider"]
        assert restored.to_dict()["memory"]["backend"] == d["memory"]["backend"]
