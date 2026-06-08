"""
Tool executor and LLM output parser.

Relocated from empire/superagi's tool_executor.py and output_parser.py.
Handles dispatching tool calls from LLM output and parsing JSON actions.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from frameworks.agents.tools import BaseTool, ToolResult, Toolkit

logger = logging.getLogger(__name__)


@dataclass
class ParsedAction:
    """An action parsed from LLM output (adapted from superagi's AgentGPTAction)."""
    name: str
    args: Dict[str, Any]


class OutputParser:
    """Parse structured actions from LLM text output.

    Handles common LLM quirks: markdown code fences, Python-style booleans,
    trailing commas, etc.

    Adapted from superagi's AgentSchemaOutputParser.
    """

    @staticmethod
    def parse(text: str) -> Optional[ParsedAction]:
        """Extract a tool action from LLM text output.

        Expects JSON like: {"tool": "name", "args": {...}}
        Also handles: {"name": "...", "args": {...}}
        """
        cleaned = OutputParser._clean_json(text)
        if not cleaned:
            return None

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.debug("Failed to parse LLM output as JSON")
            return None

        name = data.get("tool") or data.get("name") or data.get("action")
        args = data.get("args") or data.get("arguments") or data.get("input") or {}

        if not name:
            return None

        if isinstance(args, str):
            args = {"input": args}

        return ParsedAction(name=str(name), args=args)

    @staticmethod
    def _clean_json(text: str) -> str:
        """Strip markdown fences and fix common JSON issues from LLM output."""
        # Remove markdown code block wrappers
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*$", "", text)

        # Find the JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return ""
        text = match.group()

        # Fix Python-style booleans
        text = text.replace("True", "true").replace("False", "false").replace("None", "null")

        return text.strip()


class ToolExecutor:
    """Execute tool calls by name lookup and argument dispatch.

    Adapted from superagi's ToolExecutor — cleaned of DB dependencies,
    works with the GhostGoat Toolkit system.
    """

    def __init__(self, toolkit: Toolkit, finish_action: str = "finish"):
        self._toolkit = toolkit
        self._finish_action = finish_action
        self._tool_map: Dict[str, BaseTool] = {}
        self._rebuild_map()

    def _rebuild_map(self):
        """Build a normalized name -> tool lookup."""
        self._tool_map.clear()
        for tool in self._toolkit.get_tools():
            normalized = tool.name.lower().replace(" ", "").replace("_", "")
            self._tool_map[normalized] = tool

    def execute(self, action: ParsedAction) -> ToolResult:
        """Execute a parsed action against registered tools."""
        if action.name.lower() == self._finish_action:
            output = action.args.get("output") or action.args.get("response") or "Done"
            return ToolResult(output=str(output), metadata={"finished": True})

        tool = self._resolve_tool(action.name)
        if not tool:
            return ToolResult(
                output=f"Unknown tool: {action.name}. "
                       f"Available: {[t.name for t in self._toolkit.get_tools()]}",
                success=False,
            )

        return tool.execute(action.args)

    def execute_from_text(self, llm_output: str) -> ToolResult:
        """Parse LLM output and execute the resulting action."""
        action = OutputParser.parse(llm_output)
        if not action:
            return ToolResult(
                output="Could not parse a tool action from output.",
                success=False,
            )
        return self.execute(action)

    def _resolve_tool(self, name: str) -> Optional[BaseTool]:
        """Find a tool by name, case-insensitive and ignoring separators."""
        normalized = name.lower().replace(" ", "").replace("_", "")
        return self._tool_map.get(normalized)

    def run_loop(self, llm_callback: Callable, initial_prompt: str,
                 max_steps: int = 10) -> List[ToolResult]:
        """Run an agent loop: prompt LLM -> parse action -> execute -> feed back.

        Args:
            llm_callback: Callable(messages: List[Dict]) -> str
            initial_prompt: Starting system/user prompt.
            max_steps: Max iterations before forced stop.

        Returns:
            List of ToolResults from each step.
        """
        tool_descriptions = "\n".join(
            f"- {t.name}: {t.description}" for t in self._toolkit.get_tools()
        )
        tool_descriptions += f"\n- {self._finish_action}: Call when the task is complete."

        messages = [
            {"role": "system", "content": (
                "You are an agent that uses tools to accomplish tasks.\n"
                f"Available tools:\n{tool_descriptions}\n\n"
                "Respond with JSON: {\"tool\": \"name\", \"args\": {...}}\n"
                f"When done, respond with: {{\"tool\": \"{self._finish_action}\", "
                "\"args\": {\"output\": \"final answer\"}}}"
            )},
            {"role": "user", "content": initial_prompt},
        ]

        results = []
        for step in range(max_steps):
            response = llm_callback(messages)
            result = self.execute_from_text(response)
            results.append(result)

            if result.metadata.get("finished"):
                break

            # Feed tool result back as assistant + tool response
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Tool result: {result.output}"})

        return results
