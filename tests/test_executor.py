"""
Unit tests for frameworks/agents/executor.py — OutputParser and ToolExecutor.
"""

import pytest
from dataclasses import dataclass
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Minimal in-process toolkit stubs (no external deps)
# ---------------------------------------------------------------------------

@dataclass
class _FakeToolResult:
    output: str
    success: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class _FakeTool:
    def __init__(self, name: str, response: str = "tool output"):
        self.name = name
        self.description = f"A fake tool named {name}"
        self._response = response

    def execute(self, args: Dict[str, Any]) -> _FakeToolResult:
        return _FakeToolResult(output=self._response)


class _FakeToolkit:
    def __init__(self, tools: List[_FakeTool]):
        self._tools = tools

    def get_tools(self):
        return self._tools


# ---------------------------------------------------------------------------
# Patch the imports that executor.py needs
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_tool_imports(monkeypatch):
    """Make 'frameworks.agents.tools' resolve to our stubs."""
    import sys
    import types

    stub = types.ModuleType("frameworks.agents.tools")
    stub.BaseTool = _FakeTool
    stub.ToolResult = _FakeToolResult
    stub.Toolkit = _FakeToolkit
    sys.modules["frameworks.agents.tools"] = stub
    yield
    # Cleanup — remove cached executor module so it re-imports cleanly next run
    sys.modules.pop("frameworks.agents.executor", None)
    sys.modules.pop("frameworks.agents.tools", None)


def _make_executor(tools=None):
    from frameworks.agents.executor import ToolExecutor
    toolkit = _FakeToolkit(tools or [_FakeTool("search"), _FakeTool("calculate")])
    return ToolExecutor(toolkit)


# ---------------------------------------------------------------------------
# OutputParser
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestOutputParser:

    def test_parse_simple_tool_json(self):
        from frameworks.agents.executor import OutputParser
        text = '{"tool": "search", "args": {"query": "cats"}}'
        action = OutputParser.parse(text)
        assert action is not None
        assert action.name == "search"
        assert action.args == {"query": "cats"}

    def test_parse_name_key_alias(self):
        from frameworks.agents.executor import OutputParser
        text = '{"name": "calculate", "args": {"x": 1}}'
        action = OutputParser.parse(text)
        assert action.name == "calculate"

    def test_parse_action_key_alias(self):
        from frameworks.agents.executor import OutputParser
        text = '{"action": "fetch", "args": {}}'
        action = OutputParser.parse(text)
        assert action.name == "fetch"

    def test_parse_returns_none_on_empty(self):
        from frameworks.agents.executor import OutputParser
        assert OutputParser.parse("") is None

    def test_parse_returns_none_on_plain_text(self):
        from frameworks.agents.executor import OutputParser
        assert OutputParser.parse("This is just a sentence.") is None

    def test_parse_returns_none_when_no_tool_name(self):
        from frameworks.agents.executor import OutputParser
        assert OutputParser.parse('{"args": {"x": 1}}') is None

    def test_parse_strips_markdown_fences(self):
        from frameworks.agents.executor import OutputParser
        text = '```json\n{"tool": "search", "args": {}}\n```'
        action = OutputParser.parse(text)
        assert action is not None
        assert action.name == "search"

    def test_parse_fixes_python_true(self):
        from frameworks.agents.executor import OutputParser
        text = '{"tool": "check", "args": {"flag": True}}'
        action = OutputParser.parse(text)
        assert action is not None
        assert action.args["flag"] is True

    def test_parse_fixes_python_false(self):
        from frameworks.agents.executor import OutputParser
        text = '{"tool": "check", "args": {"flag": False}}'
        action = OutputParser.parse(text)
        assert action.args["flag"] is False

    def test_parse_fixes_python_none(self):
        from frameworks.agents.executor import OutputParser
        text = '{"tool": "check", "args": {"val": None}}'
        action = OutputParser.parse(text)
        assert action.args["val"] is None

    def test_parse_string_args_wrapped(self):
        from frameworks.agents.executor import OutputParser
        text = '{"tool": "echo", "args": "just a string"}'
        action = OutputParser.parse(text)
        assert action is not None
        assert action.args == {"input": "just a string"}

    def test_clean_json_extracts_from_surrounding_text(self):
        from frameworks.agents.executor import OutputParser
        text = 'Here is the action: {"tool": "run", "args": {}} — done.'
        action = OutputParser.parse(text)
        assert action is not None
        assert action.name == "run"


# ---------------------------------------------------------------------------
# ToolExecutor
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestToolExecutor:

    def test_execute_known_tool(self):
        executor = _make_executor()
        from frameworks.agents.executor import ParsedAction
        action = ParsedAction(name="search", args={"query": "test"})
        result = executor.execute(action)
        assert result.success is True

    def test_execute_unknown_tool_returns_failure(self):
        executor = _make_executor()
        from frameworks.agents.executor import ParsedAction
        action = ParsedAction(name="nonexistent_tool", args={})
        result = executor.execute(action)
        assert result.success is False
        assert "Unknown tool" in result.output

    def test_execute_finish_action(self):
        executor = _make_executor()
        from frameworks.agents.executor import ParsedAction
        action = ParsedAction(name="finish", args={"output": "all done"})
        result = executor.execute(action)
        assert result.metadata.get("finished") is True
        assert result.output == "all done"

    def test_execute_finish_default_output(self):
        executor = _make_executor()
        from frameworks.agents.executor import ParsedAction
        action = ParsedAction(name="finish", args={})
        result = executor.execute(action)
        assert result.metadata.get("finished") is True
        assert result.output  # non-empty

    def test_execute_from_text_valid(self):
        executor = _make_executor()
        result = executor.execute_from_text('{"tool": "search", "args": {}}')
        assert result.success is True

    def test_execute_from_text_unparseable(self):
        executor = _make_executor()
        result = executor.execute_from_text("not valid json at all")
        assert result.success is False
        assert "parse" in result.output.lower()

    def test_tool_name_resolution_case_insensitive(self):
        executor = _make_executor([_FakeTool("MyTool")])
        from frameworks.agents.executor import ParsedAction
        action = ParsedAction(name="mytool", args={})
        result = executor.execute(action)
        assert result.success is True

    def test_tool_name_resolution_ignores_underscores(self):
        executor = _make_executor([_FakeTool("web_search")])
        from frameworks.agents.executor import ParsedAction
        action = ParsedAction(name="websearch", args={})
        result = executor.execute(action)
        assert result.success is True

    def test_run_loop_stops_on_finish(self):
        executor = _make_executor()

        call_count = 0

        def mock_llm(messages):
            nonlocal call_count
            call_count += 1
            return '{"tool": "finish", "args": {"output": "done"}}'

        results = executor.run_loop(mock_llm, "Do something.", max_steps=10)
        assert len(results) == 1
        assert results[0].metadata.get("finished") is True
        assert call_count == 1

    def test_run_loop_respects_max_steps(self):
        executor = _make_executor([_FakeTool("loop_tool")])

        def mock_llm(messages):
            return '{"tool": "loop_tool", "args": {}}'

        results = executor.run_loop(mock_llm, "Loop forever.", max_steps=3)
        assert len(results) == 3

    def test_run_loop_feeds_result_back(self):
        executor = _make_executor([_FakeTool("search", response="found cats")])
        seen_messages = []

        def mock_llm(messages):
            seen_messages.append(messages[:])
            if len(seen_messages) == 1:
                return '{"tool": "search", "args": {}}'
            return '{"tool": "finish", "args": {"output": "done"}}'

        executor.run_loop(mock_llm, "Search for cats.", max_steps=5)
        # Second call should contain the tool result in messages
        assert len(seen_messages) >= 2
        second_call_content = " ".join(m["content"] for m in seen_messages[1])
        assert "found cats" in second_call_content
