"""
GhostGoat Training Trace Logger
================================

Every successful ReAct tool-use cycle (Thought → ACTION → OBSERVATION →
FINAL ANSWER) is captured as a JSONL record.  These records are ready-made
fine-tuning examples for Granite, Nemotron, or any instruction-tuned model
that supports function-calling / ReAct-style reasoning.

Record format (one JSON object per line):
{
  "timestamp": "2026-03-08T12:34:56",
  "user_id":   "telegram:123456",
  "system":    "<GhostGoat SYSTEM_PROMPT>",
  "user":      "search the web for latest AI news",
  "steps": [
    {"thought": "...", "action": "web_search",
     "input": {"query": "latest AI news"}, "observation": "..."},
    ...
  ],
  "final_answer": "Here is what I found …",
  "quality": "good"          # "good" | "partial" | "error"
}

The file rotates daily: traces/YYYY-MM-DD.jsonl
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TRACE_DIR = Path(os.path.expanduser("~")) / "ghostgoat_traces"


class TraceLogger:
    """Logs ReAct traces to rotating daily JSONL files."""

    def __init__(self, trace_dir: Path = TRACE_DIR):
        self._dir = trace_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def log(
        self,
        *,
        user_id: str,
        system_prompt: str,
        user_message: str,
        scratchpad: List[str],
        final_answer: str,
        quality: str = "good",
    ) -> None:
        """Parse the scratchpad and write one JSONL record."""
        try:
            steps = self._parse_scratchpad(scratchpad)
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "system": system_prompt,
                "user": user_message,
                "steps": steps,
                "final_answer": final_answer,
                "quality": quality,
                "step_count": len(steps),
            }
            self._write(record)
        except Exception as e:
            logger.debug("[TraceLogger] Failed to log trace: %s", e)

    def stats(self) -> Dict[str, Any]:
        """Return counts of trace files and total records."""
        files = sorted(self._dir.glob("*.jsonl"))
        total = 0
        for f in files:
            try:
                total += sum(1 for _ in f.open())
            except Exception:
                pass
        return {
            "trace_dir": str(self._dir),
            "files": len(files),
            "total_records": total,
            "latest": files[-1].name if files else None,
        }

    # ── Internals ──────────────────────────────────────────────────────────────

    def _write(self, record: dict) -> None:
        day = datetime.utcnow().strftime("%Y-%m-%d")
        path = self._dir / f"{day}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.debug("[TraceLogger] Wrote trace to %s", path)

    def _parse_scratchpad(self, scratchpad: List[str]) -> List[Dict[str, Any]]:
        """
        Extract structured steps from the ReAct scratchpad strings.

        Each scratchpad element looks like:
          "\nACTION: tool_name\nINPUT: {...}\nOBSERVATION: ...\nThought:"
        """
        steps = []
        _action_re = re.compile(
            r"ACTION:\s*(\w+)\s*\nINPUT:\s*(\{.*?\})\s*\nOBSERVATION:\s*(.*?)(?=\nThought:|\Z)",
            re.S,
        )
        for chunk in scratchpad:
            for m in _action_re.finditer(chunk):
                tool = m.group(1).strip()
                try:
                    inp = json.loads(m.group(2))
                except json.JSONDecodeError:
                    inp = {"raw": m.group(2)}
                obs = m.group(3).strip()[:800]   # cap observation length
                steps.append({"action": tool, "input": inp, "observation": obs})
        return steps


# Singleton
trace_logger = TraceLogger()
