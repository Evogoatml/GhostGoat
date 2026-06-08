#!/usr/bin/env python3
from typing import Dict, Any
from llm.client import LLMClient


class TaskPlanner:
    TOOL_MAP = {
        "scanner": "agents.scanner.ScannerAgent",
        "recon": "agents.recon.ReconAgent",
        "exploit": "agents.exploit.ExploitAgent",
    }

    def __init__(self, llm: LLMClient = None):
        self.llm = llm

    def plan(self, goal: str, target: str) -> Dict[str, Any]:
        if self.llm and self.llm.backend != "none":
            return self.llm.plan_task(goal, target)
        return self._fallback_plan(goal, target)

    def _fallback_plan(self, goal: str, target: str) -> Dict[str, Any]:
        steps = []
        g = goal.lower()
        if "scan" in g or "port" in g:
            steps.append({"tool": "scanner", "command": f"nmap -sV -T4 {target}", "reason": "Identify open ports and services"})
        if "recon" in g or "whois" in g or "dns" in g:
            steps.append({"tool": "recon", "command": f"whois {target}", "reason": "Gather ownership and DNS info"})
        if "tech" in g or "web" in g:
            steps.append({"tool": "recon", "command": f"whatweb {target}", "reason": "Identify web technologies"})
        if "exploit" in g or "cve" in g:
            steps.append({"tool": "exploit", "command": f"searchsploit {target}", "reason": "Search for known vulnerabilities"})
        if not steps:
            steps.append({"tool": "scanner", "command": f"nmap -sV -T4 {target}", "reason": "Default reconnaissance scan"})
        return {"steps": steps, "summary": f"Executing {len(steps)} steps against {target}"}

