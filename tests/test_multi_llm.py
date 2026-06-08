"""
Unit tests for frameworks/llm/multi_llm.py
"""

import asyncio
import pytest


def _mock_llm():
    from frameworks.llm.multi_llm import MultiLLM
    from config.unified_config import LLMConfig, LLMProvider
    cfg = LLMConfig(provider=LLMProvider.MOCK)
    return MultiLLM(cfg)


# ---------------------------------------------------------------------------
# LLMMessage / LLMResponse dataclasses
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDataClasses:

    def test_llm_message_fields(self):
        from frameworks.llm.multi_llm import LLMMessage
        msg = LLMMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_llm_response_fields(self):
        from frameworks.llm.multi_llm import LLMResponse
        resp = LLMResponse(content="hi", model="mock-llm")
        assert resp.content == "hi"
        assert resp.model == "mock-llm"
        assert resp.usage is None
        assert resp.finish_reason is None


# ---------------------------------------------------------------------------
# MockLLMInterface
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMockLLMInterface:

    def test_generate_returns_response(self):
        from frameworks.llm.multi_llm import MockLLMInterface, LLMMessage
        from config.unified_config import LLMConfig, LLMProvider
        iface = MockLLMInterface(LLMConfig(provider=LLMProvider.MOCK))
        msgs = [LLMMessage(role="user", content="What is 2+2?")]
        resp = asyncio.run(iface.generate(msgs))
        assert resp.content
        assert resp.model == "mock-llm"

    def test_generate_decompose_pattern(self):
        from frameworks.llm.multi_llm import MockLLMInterface, LLMMessage
        from config.unified_config import LLMConfig, LLMProvider
        iface = MockLLMInterface(LLMConfig(provider=LLMProvider.MOCK))
        msgs = [LLMMessage(role="user", content="Please decompose this task")]
        resp = asyncio.run(iface.generate(msgs))
        assert "tasks" in resp.content

    def test_generate_select_agent_pattern(self):
        from frameworks.llm.multi_llm import MockLLMInterface, LLMMessage
        from config.unified_config import LLMConfig, LLMProvider
        iface = MockLLMInterface(LLMConfig(provider=LLMProvider.MOCK))
        msgs = [LLMMessage(role="user", content="select agent for this task")]
        resp = asyncio.run(iface.generate(msgs))
        assert "selected_agent" in resp.content

    def test_generate_usage_populated(self):
        from frameworks.llm.multi_llm import MockLLMInterface, LLMMessage
        from config.unified_config import LLMConfig, LLMProvider
        iface = MockLLMInterface(LLMConfig(provider=LLMProvider.MOCK))
        msgs = [LLMMessage(role="user", content="hello")]
        resp = asyncio.run(iface.generate(msgs))
        assert resp.usage is not None
        assert resp.usage["total_tokens"] > 0

    def test_generate_stream_yields_strings(self):
        from frameworks.llm.multi_llm import MockLLMInterface, LLMMessage
        from config.unified_config import LLMConfig, LLMProvider
        iface = MockLLMInterface(LLMConfig(provider=LLMProvider.MOCK))
        msgs = [LLMMessage(role="user", content="hello")]
        gen = asyncio.run(iface.generate(msgs, stream=True))
        chunks = list(gen)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)
        assert "".join(chunks).strip()

    def test_generate_embedding_returns_384_dim(self):
        from frameworks.llm.multi_llm import MockLLMInterface
        from config.unified_config import LLMConfig, LLMProvider
        iface = MockLLMInterface(LLMConfig(provider=LLMProvider.MOCK))
        emb = asyncio.run(iface.generate_embedding("test text"))
        assert isinstance(emb, list)
        assert len(emb) == 384
        assert all(isinstance(v, float) for v in emb)

    def test_generate_empty_messages_does_not_crash(self):
        from frameworks.llm.multi_llm import MockLLMInterface
        from config.unified_config import LLMConfig, LLMProvider
        iface = MockLLMInterface(LLMConfig(provider=LLMProvider.MOCK))
        resp = asyncio.run(iface.generate([]))
        assert resp.content is not None


# ---------------------------------------------------------------------------
# MultiLLM
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMultiLLM:

    def test_init_with_mock_provider(self):
        from frameworks.llm.multi_llm import MultiLLM, MockLLMInterface
        from config.unified_config import LLMConfig, LLMProvider
        llm = MultiLLM(LLMConfig(provider=LLMProvider.MOCK))
        assert isinstance(llm.interface, MockLLMInterface)

    def test_init_unknown_provider_falls_back_to_mock(self):
        from frameworks.llm.multi_llm import MultiLLM, MockLLMInterface
        from config.unified_config import LLMConfig, LLMProvider
        cfg = LLMConfig(provider=LLMProvider.MOCK)
        cfg.provider = "completely_unknown"  # type: ignore[assignment]
        llm = MultiLLM(cfg)
        assert isinstance(llm.interface, MockLLMInterface)

    def test_generate_delegates_to_interface(self):
        from frameworks.llm.multi_llm import LLMMessage
        llm = _mock_llm()
        msgs = [LLMMessage(role="user", content="hello")]
        resp = asyncio.run(llm.generate(msgs))
        assert resp.content

    def test_generate_embedding_delegates(self):
        llm = _mock_llm()
        emb = asyncio.run(llm.generate_embedding("test"))
        assert len(emb) == 384

    def test_format_messages_structure(self):
        llm = _mock_llm()
        msgs = llm.format_messages(
            system_prompt="You are helpful.",
            user_message="What time is it?",
        )
        assert msgs[0].role == "system"
        assert msgs[-1].role == "user"
        assert msgs[-1].content == "What time is it?"

    def test_format_messages_includes_history(self):
        from frameworks.llm.multi_llm import LLMMessage
        llm = _mock_llm()
        history = [LLMMessage(role="assistant", content="Previous answer")]
        msgs = llm.format_messages("sys", "new question", history=history)
        roles = [m.role for m in msgs]
        assert "assistant" in roles

    def test_switch_provider_changes_interface(self):
        from frameworks.llm.multi_llm import MultiLLM, MockLLMInterface
        from config.unified_config import LLMConfig, LLMProvider
        llm = MultiLLM(LLMConfig(provider=LLMProvider.MOCK))
        llm.switch_provider(LLMProvider.MOCK)
        assert isinstance(llm.interface, MockLLMInterface)

    def test_switch_provider_updates_config(self):
        from frameworks.llm.multi_llm import MultiLLM
        from config.unified_config import LLMConfig, LLMProvider
        llm = MultiLLM(LLMConfig(provider=LLMProvider.MOCK))
        llm.switch_provider(LLMProvider.MOCK, api_key="new-key")
        assert llm.config.api_key == "new-key"


# ---------------------------------------------------------------------------
# create_llm factory
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_create_llm_with_explicit_config():
    from frameworks.llm.multi_llm import create_llm, MultiLLM
    from config.unified_config import LLMConfig, LLMProvider
    llm = create_llm(LLMConfig(provider=LLMProvider.MOCK))
    assert isinstance(llm, MultiLLM)
