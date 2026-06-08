#!/usr/bin/env python3
"""
BaseAgent + KernelClient
Every agent inherits this. Agents do not execute directly;
they request execution tokens from the Paradox Kernel via IPC.
"""

import json
import socket
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class KernelClient:
    """Mixin that connects to the Paradox Kernel over Unix socket."""

    def __init__(self, socket_path: str = "/tmp/paradox_kernel.sock"):
        self.socket_path = socket_path

    def _send(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON request to kernel and return JSON response."""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect(self.socket_path)
            sock.sendall(json.dumps(request).encode() + b"\n")

            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            sock.close()
            return json.loads(data.decode().strip())
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def register_with_kernel(self, agent_id: str, name: str, capabilities: list):
        return self._send({
            "action": "register",
            "agent_id": agent_id,
            "name": name,
            "capabilities": capabilities,
        })

    def request_execution(self, agent_id: str, command: str, target: Optional[str] = None) -> Dict[str, Any]:
        return self._send({
            "action": "execute",
            "agent_id": agent_id,
            "command": command,
            "target": target,
        })

    def report_finding(self, agent_id: str, finding: Dict[str, Any]) -> Dict[str, Any]:
        return self._send({
            "action": "report",
            "agent_id": agent_id,
            "finding": finding,
        })


class BaseAgent(ABC, KernelClient):
    """
    Abstract base for all swarm agents.
    Combines: identity, kernel IPC, skill execution, and memory hooks.
    """

    name: str = ""
    description: str = ""
    capabilities: list = []
    agent_id: str = ""

    def __init__(self, agent_id: str = ""):
        super().__init__()
        self.agent_id = agent_id or self.name
        self.memory: list = []

    def register(self) -> Dict[str, Any]:
        return self.register_with_kernel(
            agent_id=self.agent_id,
            name=self.name,
            capabilities=self.capabilities,
        )

    def execute(self, task: str, context: Dict[str, Any] = None) -> str:
        """
        Main entrypoint. Agents parse task, build command,
        request kernel execution, and return formatted result.
        """
        command = self._build_command(task, context or {})
        target = context.get("target") if context else None

        result = self.request_execution(self.agent_id, command, target)

        if result.get("status") == "denied":
            return f"🛡️  Kernel denied: {result.get('reason')}"

        if result.get("status") == "error":
            return f"❌ Kernel error: {result.get('reason')}"

        # Handle failed execution (sandbox error, timeout, etc)
        killed = result.get("killed", False)
        kill_reason = result.get("kill_reason", "")
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        warnings = result.get("warnings", [])

        if killed:
            msg = f"⚠️  Task killed ({kill_reason})"
            if stderr:
                msg += f"\nError: {stderr[:800]}"
            return msg

        # If no stdout but stderr exists, show stderr
        if not stdout.strip() and stderr.strip():
            return f"⚠️  No output. Error:\n{stderr[:2000]}"

        # Add warnings if any
        formatted = self._format_output(stdout, stderr, context)
        if warnings:
            formatted = "📝 Warnings:\n" + "\n".join(f"  - {w}" for w in warnings) + "\n\n" + formatted

        return formatted

    @abstractmethod
    def _build_command(self, task: str, context: Dict[str, Any]) -> str:
        """Override: convert task + context into a shell command."""
        pass

    def _format_output(self, stdout: str, stderr: str, context: Dict[str, Any]) -> str:
        """Override: format raw sandbox output for user/agent consumption."""
        return stdout[:4000]

    def remember(self, key: str, value: Any):
        self.memory.append({"key": key, "value": value, "timestamp": __import__("time").time()})

