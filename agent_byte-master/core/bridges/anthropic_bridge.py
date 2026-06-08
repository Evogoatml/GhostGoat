"""
AnthropicBridge — direct Claude API access with streaming, tool use, and vision.
All agents that need advanced Claude features use this instead of the LLMController.
"""
from __future__ import annotations
import base64
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnthropicBridge:
    """Full-featured Anthropic Claude bridge."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        return self._client

    def chat(self, prompt: str, system: str = "", model: str = "claude-sonnet-4-20250514",
             max_tokens: int = 4096) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs: Dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            kwargs["system"] = system
        response = self._get_client().messages.create(**kwargs)
        return response.content[0].text

    def chat_with_tools(self, prompt: str, tools: List[Dict], system: str = "",
                        model: str = "claude-sonnet-4-20250514") -> Dict:
        """Chat with tool use — returns full response dict."""
        messages = [{"role": "user", "content": prompt}]
        kwargs: Dict[str, Any] = {
            "model": model, "max_tokens": 4096,
            "messages": messages, "tools": tools,
        }
        if system:
            kwargs["system"] = system
        response = self._get_client().messages.create(**kwargs)
        result = {"stop_reason": response.stop_reason, "content": []}
        for block in response.content:
            if block.type == "text":
                result["content"].append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                result["content"].append({
                    "type": "tool_use", "name": block.name,
                    "id": block.id, "input": block.input,
                })
        return result

    def vision(self, prompt: str, image_path: str, model: str = "claude-sonnet-4-20250514") -> str:
        """Send image + prompt to Claude vision."""
        with open(image_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        ext = image_path.rsplit(".", 1)[-1].lower()
        media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                     "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
        media_type = media_map.get(ext, "image/jpeg")
        response = self._get_client().messages.create(
            model=model, max_tokens=4096,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": prompt},
            ]}],
        )
        return response.content[0].text

    async def stream(self, prompt: str, on_token=None, model: str = "claude-sonnet-4-20250514") -> str:
        """Stream response tokens. Calls on_token(text) for each chunk."""
        full = []
        with self._get_client().messages.stream(
            model=model, max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                full.append(text)
                if on_token:
                    on_token(text)
        return "".join(full)


anthropic_bridge = AnthropicBridge()
