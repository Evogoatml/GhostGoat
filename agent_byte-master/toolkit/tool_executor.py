"""
GhostGoat ToolExecutor — Runs selected tools, chains them, handles errors, captures output.
"""
import json, logging
from typing import Any, Dict, List
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes a pipeline of tool calls, handling dependencies and error recovery."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.history: List[Dict[str, Any]] = []

    async def run(self, selections: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute each selected tool sequentially, passing prior results as context.
        selections = [{"tool": "nmap_scan", "arguments": {"target": "..."}, "reason": "..."}]
        """
        results = []
        ctx = context or {}
        shared = {}  # Accumulated outputs for multi-step chaining

        for idx, sel in enumerate(selections):
            tool_name = sel.get("tool", "")
            args = dict(sel.get("arguments", {}))
            reason = sel.get("reason", "")
            tool = self.registry.get(tool_name)

            if not tool:
                logger.warning("Tool not found: %s", tool_name)
                results.append({
                    "tool": tool_name,
                    "status": "failed",
                    "error": f"Tool '{tool_name}' not found",
                    "output": None,
                })
                continue

            # Substitute context references in args
            args = self._substitute_context(args, shared)

            logger.info("Executing [%d/%d] %s: %s", idx + 1, len(selections), tool_name, reason)
            output = tool.run(args) if tool.run else {"success": False, "error": "No runner"}

            entry = {
                "tool": tool_name,
                "status": "done" if output.get("success") else "failed",
                "arguments": args,
                "reason": reason,
                "output": output,
                "dangerous": tool.dangerous,
            }
            results.append(entry)
            self.history.append(entry)

            # Store key outputs for context chaining
            if output.get("success"):
                if "stdout" in output:
                    shared[f"{tool_name}_stdout"] = output["stdout"]
                if "result" in output:
                    shared[f"{tool_name}_result"] = output["result"]
            shared[f"{tool_name}_full"] = output

        return results

    def run_single(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool directly."""
        tool = self.registry.get(tool_name)
        if not tool or not tool.run:
            return {"success": False, "error": f"Tool '{tool_name}' unavailable"}
        return tool.run(args)

    def _substitute_context(self, args: Dict[str, Any], shared: Dict[str, Any]) -> Dict[str, Any]:
        """Replace {{var}} placeholders in arguments with shared context values."""
        out = {}
        for k, v in args.items():
            if isinstance(v, str):
                for sk, sv in shared.items():
                    if isinstance(sv, str) and f"{{{sk}}}" in v:
                        v = v.replace(f"{{{sk}}}", sv)
                out[k] = v
            else:
                out[k] = v
        return out

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.history)

    def last_output(self, tool_name: str = None) -> Any:
        """Get the most recent output, optionally filtered by tool name."""
        for entry in reversed(self.history):
            if tool_name is None or entry["tool"] == tool_name:
                return entry.get("output")
        return None

    def synthesize_pipeline_report(self, results: List[Dict[str, Any]], goal: str = "") -> str:
        """Build a human-readable report from pipeline results."""
        lines = [f"🎯 *Goal:* {goal[:150]}", f"📊 *Tools executed:* {len(results)}", ""]
        ok = sum(1 for r in results if r["status"] == "done")
        fail = sum(1 for r in results if r["status"] == "failed")
        lines.append(f"✅ Success: {ok} | ❌ Failed: {fail}")
        lines.append("")

        for r in results:
            icon = "✅" if r["status"] == "done" else "❌"
            tool_name = r["tool"]
            reason = r.get("reason", "")
            out = r.get("output", {})
            summary = ""
            if isinstance(out, dict):
                if "stdout" in out and out["stdout"]:
                    summary = out["stdout"][:400]
                elif "result" in out and out["result"]:
                    summary = str(out["result"])[:400]
                elif "error" in out and out["error"]:
                    summary = f"Error: {out['error'][:200]}"
            lines.append(f"{icon} *{tool_name}* — {reason}")
            if summary:
                lines.append(f"   ```{summary}```")
            lines.append("")

        return "\n".join(lines)

