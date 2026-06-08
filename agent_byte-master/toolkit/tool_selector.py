"""
GhostGoat ToolSelector — LLM-based reasoning to select the right tool(s) for a task.
"""
import json, re, subprocess, os
from typing import Any, Dict, List, Optional, Tuple
from .tool_registry import ToolRegistry, Tool


def ollama(prompt: str, system: str = "", model: str = "llama3.2", timeout: int = 30) -> str:
    full = f"System: {system}\nUser: {prompt}\nAI:"
    try:
        r = subprocess.run(["ollama", "run", model, full], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


class ToolSelector:
    """Uses LLM + symbolic pre-filter to pick tools and extract arguments."""

    def __init__(self, registry: ToolRegistry, model: str = "llama3.2"):
        self.registry = registry
        self.model = model

    def select(self, task: str, available_tools: Optional[List[str]] = None, fast_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Select tools for a task.
        Returns a list of dicts: [{"tool": "nmap_scan", "reason": "...", "arguments": {"target": "..."}}]
        """
        # Phase 1: Fast symbolic pre-filter
        candidates = self._symbolic_filter(task)
        if not candidates:
            candidates = list(self.registry.tools.values())
        if available_tools:
            candidates = [t for t in candidates if t.name in available_tools]

        # Phase 2: If fast_mode, just pick top candidate by keyword scoring
        if fast_mode:
            top = candidates[0] if candidates else None
            if top:
                args = self._extract_args_simple(task, top)
                return [{"tool": top.name, "reason": f"Keyword match for {top.category}", "arguments": args}]
            return []

        # Phase 3: LLM reasoning for tool selection
        tool_prompt = self._build_tool_prompt(candidates[:6])
        system = (
            "You are a tool selection engine. Given a user's task and available tools, "
            "pick the best tool(s) and extract the required arguments. "
            "Output ONLY valid JSON: [{\"tool\": \"name\", \"reason\": \"why\", \"arguments\": {...}}]. "
            "Be precise. Only select tools that are actually needed for the task."
        )
        user_prompt = (
            f"Task: {task}\n\n"
            f"Available Tools:\n{tool_prompt}\n\n"
            f"Select the best tool(s) and extract arguments. If multiple tools are needed in sequence, include all."
        )
        raw = ollama(user_prompt, system=system, model=self.model, timeout=30)

        # Parse JSON
        selections = self._parse_json_array(raw)
        if selections:
            # Validate tool names exist
            valid = [s for s in selections if s.get("tool") in self.registry.tools]
            if valid:
                # Enrich with argument extraction for any missing params
                for sel in valid:
                    tool = self.registry.get(sel["tool"])
                    if tool:
                        sel["arguments"] = self._enrich_args(task, sel.get("arguments", {}), tool)
                return valid

        # Phase 4: Ultimate fallback — rule-based selection
        return self._rule_fallback(task, candidates)

    def _symbolic_filter(self, task: str) -> List[Tool]:
        """Pre-filter candidates using keyword scoring."""
        return self.registry.suggest_for_task(task)

    def _build_tool_prompt(self, tools: List[Tool]) -> str:
        return "\n\n".join(t.to_prompt() for t in tools)

    def _parse_json_array(self, text: str) -> List[Dict[str, Any]]:
        """Extract JSON array from LLM output."""
        if not text:
            return []
        try:
            # Try direct parse
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
        # Try line-by-line JSON objects
        results = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    results.append(json.loads(line))
                except:
                    pass
        return results

    def _rule_fallback(self, task: str, candidates: List[Tool]) -> List[Dict[str, Any]]:
        """When LLM fails, use hardcoded rules."""
        t = task.lower()
        # Domain/IP extraction
        domains = re.findall(r'([a-z0-9.-]+\.(?:com|net|org|io|dev|app|co|ai|xyz|local|gov|edu|mil))', t)
        ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)', t)
        target = domains[0] if domains else (ips[0] if ips else "")
        urls = re.findall(r'https?://[^\s]+', t)
        url = urls[0] if urls else (f"http://{target}" if target else "")

        selections = []

        if "scan" in t or "port" in t or "nmap" in t:
            selections.append({"tool": "nmap_scan", "reason": "Port scanning requested", "arguments": {"target": target, "flags": "-sV --top-ports 1000"}})

        if "dns" in t or "subdomain" in t or "subfinder" in t:
            selections.append({"tool": "dns_recon", "reason": "DNS reconnaissance", "arguments": {"domain": target, "mode": "all"}})

        if "whois" in t or "registration" in t or "owner" in t:
            selections.append({"tool": "whois_lookup", "reason": "Domain registration info", "arguments": {"domain": target}})

        if "header" in t or "banner" in t or "server" in t or "http" in t:
            selections.append({"tool": "web_headers", "reason": "HTTP header analysis", "arguments": {"url": url}})

        if "directory" in t or "dirb" in t or "gobuster" in t or "hidden" in t or "admin" in t:
            selections.append({"tool": "dir_enum", "reason": "Directory enumeration", "arguments": {"url": url}})

        if "nikto" in t or "web vuln" in t or "outdated" in t:
            selections.append({"tool": "nikto_scan", "reason": "Web vulnerability scan", "arguments": {"host": target or url}})

        if "exploit" in t or "searchsploit" in t or "cve" in t:
            # Extract software name from task
            query = task
            selections.append({"tool": "searchsploit", "reason": "Search for known exploits", "arguments": {"query": query}})

        if "payload" in t or "xss" in t or "sqli" in t or "lfi" in t or "rce" in t:
            cat = "XSS" if "xss" in t else ("SQL Injection" if "sql" in t else "RCE")
            selections.append({"tool": "payload_search", "reason": "Find attack payloads", "arguments": {"category": cat}})

        if "hash" in t or "md5" in t or "sha" in t:
            # Extract the string to hash
            words = t.split()
            inp = words[-1] if words else "test"
            algo = "md5" if "md5" in t else "sha256"
            selections.append({"tool": "hash_compute", "reason": "Compute hash digest", "arguments": {"input": inp, "algorithm": algo}})

        if "python" in t or "code" in t or "script" in t:
            selections.append({"tool": "python_exec", "reason": "Execute/generate Python code", "arguments": {"code": "# TODO: extract from request"}})

        if "research" in t or "explain" in t or "what is" in t or "how does" in t:
            selections.append({"tool": "ollama_research", "reason": "Qualitative research via LLM", "arguments": {"query": task}})

        if "remember" in t or "memory" in t or "recall" in t:
            selections.append({"tool": "memory_recall", "reason": "Search internal memory", "arguments": {"query": task}})

        if not selections and candidates:
            # Just pick the top candidate
            top = candidates[0]
            args = self._extract_args_simple(task, top)
            selections.append({"tool": top.name, "reason": "Best available match", "arguments": args})

        if not selections:
            selections.append({"tool": "ollama_research", "reason": "Fallback: general research", "arguments": {"query": task}})

        return selections

    def _extract_args_simple(self, task: str, tool: Tool) -> Dict[str, Any]:
        """Basic argument extraction from natural language."""
        args = {}
        t = task.lower()

        # Extract domains/IPs universally
        domains = re.findall(r'([a-z0-9.-]+\.(?:com|net|org|io|dev|app|co|ai|xyz|local|gov|edu|mil))', t)
        ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)', t)
        urls = re.findall(r'https?://[^\s]+', t)
        target = domains[0] if domains else (ips[0] if ips else "")
        url = urls[0] if urls else (f"http://{target}" if target else "")

        for param in tool.parameters:
            if param.name == "target":
                args["target"] = target
            elif param.name == "domain":
                args["domain"] = target
            elif param.name == "url":
                args["url"] = url
            elif param.name == "host":
                args["host"] = target or url
            elif param.name == "query":
                args["query"] = task
            elif param.name == "input":
                args["input"] = task
            elif param.name == "category":
                # Infer category from task
                if "xss" in t: args["category"] = "XSS"
                elif "sql" in t: args["category"] = "SQL Injection"
                elif "lfi" in t: args["category"] = "LFI"
                elif "rce" in t: args["category"] = "RCE"
                elif "ssrf" in t: args["category"] = "SSRF"
                elif "xxe" in t: args["category"] = "XXE"
                else: args["category"] = "General"
            elif param.name == "code":
                args["code"] = "# Extract code from request"
            elif param.name == "command":
                args["command"] = task
            elif not param.required:
                args[param.name] = param.default

        return args

    def _enrich_args(self, task: str, existing: Dict[str, Any], tool: Tool) -> Dict[str, Any]:
        """Fill in any missing required parameters."""
        enriched = dict(existing)
        defaults = self._extract_args_simple(task, tool)
        for param in tool.parameters:
            if param.name not in enriched or not enriched[param.name]:
                if param.name in defaults:
                    enriched[param.name] = defaults[param.name]
                elif not param.required:
                    enriched[param.name] = param.default
        return enriched

