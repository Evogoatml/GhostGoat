"""
GhostGoat AdaptiveExecutor — Parallel execution, retry with alternates,
output chaining, and self-healing error recovery.
"""
import asyncio, logging, time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from .tool_registry import ToolRegistry
from .tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


@dataclass
class ExecutionNode:
    id: str
    tool: str
    arguments: Dict[str, Any]
    reason: str
    depends_on: List[str] = field(default_factory=list)
    status: str = "pending"   # pending | running | done | failed
    output: Dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    max_retries: int = 2
    alternate_tool: Optional[str] = None


class AdaptiveExecutor:
    """
    Executes a DAG of tool calls with:
    - Parallel dispatch for independent nodes
    - Retry with exponential backoff on failure
    - Alternate tool substitution
    - Output chaining via {{var}} substitution
    - ReAct: inspect output and spawn follow-up nodes
    """

    def __init__(self, registry: ToolRegistry, max_parallel: int = 4):
        self.registry = registry
        self.base = ToolExecutor(registry)
        self.max_parallel = max_parallel

    async def run_dag(self, nodes: List[ExecutionNode], context: Dict[str, Any] = None) -> List[ExecutionNode]:
        """Execute a DAG of nodes respecting dependencies."""
        ctx = context or {}
        completed: Set[str] = set()
        running: Dict[str, asyncio.Task] = {}
        pending: Dict[str, ExecutionNode] = {n.id: n for n in nodes}
        retried_queue: List[ExecutionNode] = []

        while pending or running or retried_queue:
            # Re-add retried nodes to pending
            while retried_queue:
                n = retried_queue.pop(0)
                n.status = "pending"
                pending[n.id] = n

            # Start eligible nodes
            eligible = [
                nid for nid, n in pending.items()
                if n.status == "pending"
                and all(d in completed for d in n.depends_on)
                and nid not in running
            ]

            for nid in eligible[:self.max_parallel - len(running)]:
                n = pending.pop(nid)
                n.status = "running"
                task = asyncio.create_task(self._run_node(n, ctx, completed, retried_queue))
                running[nid] = task

            if not running:
                if pending:
                    logger.warning("Deadlock: %d pending nodes blocked", len(pending))
                    for n in pending.values():
                        n.status = "failed"
                        n.output = {"success": False, "error": "Dependency deadlock"}
                    completed.update(pending.keys())
                break

            done_tasks, _ = await asyncio.wait(
                list(running.values()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done_tasks:
                for nid, t in list(running.items()):
                    if t == task:
                        del running[nid]
                        break

        return list(nodes)

    async def _run_node(self, node: ExecutionNode, ctx: Dict[str, Any], completed: Set[str], retried_queue: List[ExecutionNode]) -> None:
        tool = self.registry.get(node.tool)
        if not tool:
            node.status = "failed"
            node.output = {"success": False, "error": f"Tool '{node.tool}' not found"}
            completed.add(node.id)
            return

        args = self.base._substitute_context(node.arguments, ctx)
        start = time.time()

        try:
            output = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, lambda: tool.run(args)),
                timeout=tool.timeout + 5
            )
            latency = (time.time() - start) * 1000
            node.output = output
            success = output.get("success", False)

            if success:
                node.status = "done"
                if "stdout" in output:
                    ctx[f"{node.id}_stdout"] = output["stdout"]
                if "result" in output:
                    ctx[f"{node.id}_result"] = output["result"]
                ctx[f"{node.id}_full"] = output
                logger.info("Node %s: %s OK in %.0fms", node.id, node.tool, latency)
                completed.add(node.id)
            else:
                await self._handle_failure(node, args, ctx, completed, retried_queue)

        except asyncio.TimeoutError:
            node.output = {"success": False, "error": f"Timeout after {tool.timeout}s"}
            await self._handle_failure(node, args, ctx, completed, retried_queue)
        except Exception as e:
            node.output = {"success": False, "error": str(e)}
            await self._handle_failure(node, args, ctx, completed, retried_queue)

    async def _handle_failure(self, node: ExecutionNode, args: Dict[str, Any], ctx: Dict[str, Any], completed: Set[str], retried_queue: List[ExecutionNode]) -> None:
        if node.retries < node.max_retries:
            node.retries += 1
            logger.info("Node %s: retry %d/%d", node.id, node.retries, node.max_retries)
            await asyncio.sleep(min(2 ** node.retries, 10))
            retried_queue.append(node)
            return

        if node.alternate_tool:
            alt = self.registry.get(node.alternate_tool)
            if alt:
                logger.info("Node %s: fallback to %s", node.id, node.alternate_tool)
                try:
                    output = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, lambda: alt.run(args)),
                        timeout=alt.timeout + 5
                    )
                    node.output = output
                    node.tool = node.alternate_tool
                    if output.get("success"):
                        node.status = "done"
                        ctx[f"{node.id}_stdout"] = output.get("stdout", "")
                        ctx[f"{node.id}_result"] = output.get("result", "")
                        completed.add(node.id)
                        return
                except Exception as e:
                    node.output = {"success": False, "error": f"Alternate failed: {str(e)}"}

        node.status = "failed"
        completed.add(node.id)

    def build_dag_from_selections(self, selections: List[Dict[str, Any]]) -> List[ExecutionNode]:
        nodes = []
        prev_id = None
        for i, sel in enumerate(selections):
            nid = f"n{i}"
            depends = [prev_id] if prev_id else []
            nodes.append(ExecutionNode(
                id=nid,
                tool=sel["tool"],
                arguments=sel.get("arguments", {}),
                reason=sel.get("reason", ""),
                depends_on=depends,
                alternate_tool=self._infer_alternate(sel["tool"]),
            ))
            prev_id = nid
        return nodes

    def _infer_alternate(self, tool_name: str) -> Optional[str]:
        alternates = {
            "nmap_scan": "shell_exec",
            "dns_recon": "shell_exec",
            "dir_enum": "shell_exec",
            "nikto_scan": "web_headers",
            "searchsploit": "ollama_research",
            "payload_search": "ollama_research",
        }
        return alternates.get(tool_name)

    def react_next_step(self, goal: str, completed_nodes: List[ExecutionNode]) -> Optional[ExecutionNode]:
        for node in completed_nodes:
            if node.status != "done":
                continue
            out = node.output
            stdout = out.get("stdout", "")

            if node.tool == "nmap_scan":
                if any(p in stdout for p in ["80/tcp", "443/tcp", "8080/tcp", "8443/tcp"]):
                    target = node.arguments.get("target", "")
                    url = f"http://{target}" if target else ""
                    if url:
                        return ExecutionNode(
                            id="react_web_enum",
                            tool="dir_enum",
                            arguments={"url": url},
                            reason=f"Web port open on {target}, enumerating directories",
                        )

            if node.tool == "web_headers":
                server = stdout.lower()
                if any(s in server for s in ["apache", "nginx", "iis", "tomcat"]):
                    url = node.arguments.get("url", "")
                    if url:
                        return ExecutionNode(
                            id="react_nikto",
                            tool="nikto_scan",
                            arguments={"host": url},
                            reason="Known web server detected, running vulnerability scan",
                        )

            if node.tool == "dns_recon":
                subs = [line.strip() for line in stdout.splitlines() if line.strip() and not line.startswith(";")]
                if subs:
                    sub = subs[0]
                    if "." in sub:
                        return ExecutionNode(
                            id="react_sub_scan",
                            tool="nmap_scan",
                            arguments={"target": sub, "flags": "-sV --top-ports 100"},
                            reason=f"Subdomain {sub} discovered, quick port scan",
                        )

        return None

    def synthesize_report(self, nodes: List[ExecutionNode], goal: str = "") -> str:
        lines = [f"🎯 *Goal:* {goal[:150]}", f"📊 *Nodes executed:* {len(nodes)}", ""]
        ok = sum(1 for n in nodes if n.status == "done")
        fail = sum(1 for n in nodes if n.status == "failed")
        retry = sum(1 for n in nodes if n.retries > 0)
        lines.append(f"✅ Success: {ok} | ❌ Failed: {fail} | 🔄 Retried: {retry}")
        lines.append("")

        for n in nodes:
            icon = "✅" if n.status == "done" else "❌"
            out = n.output
            summary = ""
            if isinstance(out, dict):
                if "stdout" in out and out["stdout"]:
                    summary = out["stdout"][:400]
                elif "result" in out and out["result"]:
                    summary = str(out["result"])[:400]
                elif "error" in out and out["error"]:
                    summary = f"Error: {out['error'][:200]}"
            retry_str = f" (retried {n.retries}x)" if n.retries > 0 else ""
            lines.append(f"{icon} *{n.tool}* — {n.reason}{retry_str}")
            if summary:
                lines.append(f"   ```{summary}```")
            lines.append("")

        return "\n".join(lines)

