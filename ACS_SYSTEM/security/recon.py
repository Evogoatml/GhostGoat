#!/usr/bin/env python3
"""
🌐 Recon Agent
Information gathering: whois, dns, tech detection.
"""

from .base import BaseAgent


class ReconAgent(BaseAgent):
    name = "recon"
    description = "Target reconnaissance and OSINT"
    capabilities = ["recon", "whois", "dns", "tech_detect", "whatweb"]

    def _build_command(self, task: str, context: dict) -> str:
        target = context.get("target", task.strip().split()[-1] if task else "")

        if "whois" in task.lower():
            return f"whois {target}"
        elif "dns" in task.lower() or "dig" in task.lower():
            return f"dig +short {target}"
        elif "tech" in task.lower() or "whatweb" in task.lower():
            return f"whatweb {target}"
        else:
            return f"whatweb {target}"

    def _format_output(self, stdout: str, stderr: str, context: dict) -> str:
        return stdout[:4000] if stdout.strip() else stderr[:2000]

