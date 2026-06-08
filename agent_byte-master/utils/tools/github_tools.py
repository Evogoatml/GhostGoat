"""
GitHub tools.

Relocated from empire/superagi's GitHub tool suite.
Provides repo search and AI-powered PR review.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

from frameworks.agents.tools import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class GitHubSearchTool(BaseTool):
    """Search for files in a GitHub repository.

    Requires: pip install requests
    Config: GITHUB_ACCESS_TOKEN
    """

    name = "github_search"
    description = "Search for a file in a GitHub repository by owner, repo, and filename."

    def _execute(self, owner: str, repo: str, filename: str,
                 folder: str = "", **kwargs) -> ToolResult:
        import requests

        token = self.get_config("GITHUB_ACCESS_TOKEN")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        query = f"filename:{filename}+repo:{owner}/{repo}"
        if folder:
            query += f"+path:{folder}"

        url = f"https://api.github.com/search/code?q={query}"
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code != 200:
            return ToolResult(output=f"GitHub API error: {resp.status_code}", success=False)

        data = resp.json()
        items = data.get("items", [])
        if not items:
            return ToolResult(output=f"No files matching '{filename}' found in {owner}/{repo}.")

        lines = []
        for item in items[:10]:
            lines.append(f"- {item['path']}  ({item['html_url']})")

        return ToolResult(
            output=f"Found {data['total_count']} result(s):\n" + "\n".join(lines),
            metadata={"total_count": data["total_count"]},
        )

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "filename": {"type": "string", "description": "File name to search for"},
                "folder": {"type": "string", "description": "Optional folder path to narrow search"},
            },
            "required": ["owner", "repo", "filename"],
        }


class GitHubPRReviewTool(BaseTool):
    """AI-powered pull request code review.

    Fetches a PR diff, splits it into reviewable chunks, and uses an LLM
    callback to generate review comments.

    Relocated from superagi's review_pull_request.py — stripped of ORM
    coupling, uses a callback for LLM calls instead.

    Requires: pip install requests
    Config: GITHUB_ACCESS_TOKEN
    """

    name = "github_pr_review"
    description = "Review a GitHub pull request using AI. Fetches diff and generates comments."

    def __init__(self, llm_callback=None, max_tokens_per_chunk: int = 3000,
                 config: Optional[Dict[str, str]] = None):
        """
        Args:
            llm_callback: Callable(prompt: str) -> str.  If None, returns raw diff.
            max_tokens_per_chunk: Approximate token budget per review chunk.
        """
        super().__init__(config)
        self._llm = llm_callback
        self._chunk_tokens = max_tokens_per_chunk

    def _execute(self, owner: str, repo: str, pr_number: int, **kwargs) -> ToolResult:
        import requests

        token = self.get_config("GITHUB_ACCESS_TOKEN")
        headers = {
            "Accept": "application/vnd.github.v3.diff",
        }
        if token:
            headers["Authorization"] = f"token {token}"

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code != 200:
            return ToolResult(output=f"GitHub API error: {resp.status_code}", success=False)

        diff_text = resp.text
        if not diff_text.strip():
            return ToolResult(output="PR has no diff content.")

        if not self._llm:
            return ToolResult(
                output=diff_text[:5000],
                metadata={"pr": pr_number, "note": "No LLM callback — returning raw diff"},
            )

        # Split diff into chunks and review each
        chunks = self._split_diff(diff_text)
        reviews = []
        for i, chunk in enumerate(chunks):
            prompt = (
                f"Review the following code diff (part {i+1}/{len(chunks)}) "
                f"from PR #{pr_number} in {owner}/{repo}.\n"
                f"Point out bugs, security issues, style problems, and suggest improvements.\n\n"
                f"```diff\n{chunk}\n```"
            )
            review = self._llm(prompt)
            reviews.append(review)

        combined = "\n\n---\n\n".join(reviews)
        return ToolResult(
            output=combined,
            metadata={"pr": pr_number, "chunks_reviewed": len(chunks)},
        )

    def _split_diff(self, diff: str):
        """Split a diff into chunks that fit within the token budget."""
        # Rough estimate: 1 token ~= 4 chars
        char_limit = self._chunk_tokens * 4
        chunks = []
        current = []
        current_len = 0

        for line in diff.split("\n"):
            line_len = len(line) + 1
            if current_len + line_len > char_limit and current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            current.append(line)
            current_len += line_len

        if current:
            chunks.append("\n".join(current))

        return chunks

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "pr_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pr_number"],
        }
