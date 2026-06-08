"""
Code generation and improvement tools.

Relocated from empire/superagi's CodingTool and ImproveCodeTool.
Uses an LLM callback for generation — no ORM or file manager coupling.
"""

import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from frameworks.agents.tools import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CodeGenerationTool(BaseTool):
    """Generate code files from a natural-language description using an LLM.

    Requires an llm_callback: Callable(prompt: str) -> str.
    """

    name = "code_generate"
    description = "Generate code from a description. Returns generated file contents."

    def __init__(self, llm_callback: Callable, output_dir: str = ".",
                 config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self._llm = llm_callback
        self._output_dir = output_dir

    def _execute(self, description: str, language: str = "python",
                 save: bool = False, **kwargs) -> ToolResult:
        prompt = (
            f"Generate {language} code for the following requirement.\n"
            f"Return ONLY code wrapped in markdown code blocks with filenames.\n"
            f"Use the format:\n"
            f"```filename.py\n<code>\n```\n\n"
            f"Requirement: {description}"
        )

        response = self._llm(prompt)
        files = self._extract_code_blocks(response)

        if not files:
            return ToolResult(output=response, metadata={"note": "No code blocks parsed"})

        if save:
            self._save_files(files)

        parts = []
        for fname, code in files:
            parts.append(f"### {fname}\n```\n{code}\n```")

        return ToolResult(
            output="\n\n".join(parts),
            metadata={"files": [f for f, _ in files], "saved": save},
        )

    def _extract_code_blocks(self, text: str) -> List[Tuple[str, str]]:
        """Extract (filename, code) pairs from markdown code blocks."""
        pattern = r"```(\S+)\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        results = []
        for header, code in matches:
            # header might be "python" (language) or "app.py" (filename)
            if "." in header:
                filename = header
            else:
                filename = f"generated.{header}"
            results.append((filename, code.strip()))
        return results

    def _save_files(self, files: List[Tuple[str, str]]):
        os.makedirs(self._output_dir, exist_ok=True)
        for fname, code in files:
            path = os.path.join(self._output_dir, fname)
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
            with open(path, "w") as f:
                f.write(code)
            logger.info("Saved generated file: %s", path)

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What code to generate"},
                "language": {"type": "string", "description": "Programming language (default: python)"},
                "save": {"type": "boolean", "description": "Save files to disk"},
            },
            "required": ["description"],
        }


class CodeImprovementTool(BaseTool):
    """Improve existing code using an LLM.

    Reads code, sends it through an LLM for improvement, returns the result.
    """

    name = "code_improve"
    description = "Improve existing code by sending it through an LLM for review and enhancement."

    def __init__(self, llm_callback: Callable,
                 config: Optional[Dict[str, str]] = None):
        super().__init__(config)
        self._llm = llm_callback

    def _execute(self, code: str, instructions: str = "Improve this code",
                 **kwargs) -> ToolResult:
        prompt = (
            f"{instructions}\n\n"
            f"Return the improved code wrapped in a markdown code block.\n\n"
            f"```\n{code}\n```"
        )

        response = self._llm(prompt)

        # Try to extract code block from response
        match = re.search(r"```(?:\w+)?\n(.*?)```", response, re.DOTALL)
        improved = match.group(1).strip() if match else response

        return ToolResult(
            output=improved,
            metadata={"instructions": instructions},
        )

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code to improve"},
                "instructions": {"type": "string", "description": "Improvement instructions"},
            },
            "required": ["code"],
        }
