#!/usr/bin/env python3
"""
🔍 Scanner Agent
Port and vulnerability scanning through kernel-sandboxed execution.
"""

from .base import BaseAgent


class ScannerAgent(BaseAgent):
    name = "scanner"
    description = "Port & service scanning with nmap"
    capabilities = ["scan", "nmap", "port_enum", "service_detection"]

    def _build_command(self, task: str, context: dict) -> str:
        target = context.get("target", task.strip().split()[-1] if task else "")

        flags = "-sV -T4"
        if "fast" in task.lower():
            flags = "-sS -T5 --top-ports 100"
        elif "full" in task.lower():
            flags = "-sV -sC -T4 -p-"
        elif "udp" in task.lower():
            flags = "-sU -T4"

        return f"nmap {flags} {target}"

    def _format_output(self, stdout: str, stderr: str, context: dict) -> str:
        lines = stdout.splitlines()
        ports = [l for l in lines if "/tcp" in l or "/udp" in l]
        if ports:
            summary = f"🔍 Found {len(ports)} open ports\n"
            summary += "\n".join(ports[:20])
            if len(ports) > 20:
                summary += f"\n... ({len(ports) - 20} more)"
            return summary
        # No ports found or non-standard output — return raw
        return stdout[:4000] if stdout.strip() else stderr[:2000]

