"""
GhostGoat ToolRegistry — Rich tool definitions with schemas, examples, and usage guidance.
Every tool has: name, description, when_to_use, parameters, examples, and a run function.
"""
import re, subprocess, os, json, asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from functools import partial


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    examples: List[str] = field(default_factory=list)


@dataclass
class Tool:
    name: str
    description: str
    when_to_use: str
    category: str
    parameters: List[ToolParameter]
    examples: List[str] = field(default_factory=list)
    dangerous: bool = False
    timeout: int = 60
    run: Optional[Callable] = None

    def to_prompt(self) -> str:
        lines = [
            f"### {self.name}",
            f"Description: {self.description}",
            f"When to use: {self.when_to_use}",
            f"Category: {self.category}",
            f"Parameters:",
        ]
        for p in self.parameters:
            req = "required" if p.required else f"optional (default: {p.default})"
            lines.append(f"  - {p.name} ({p.type}) — {p.description} [{req}]")
        if self.examples:
            lines.append(f"Examples:")
            for e in self.examples:
                lines.append(f"  - {e}")
        return "\n".join(lines)


class ToolRegistry:
    """Central registry of all available tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_all()

    def _register_all(self):
        # ═══════════════════════════════════════════════════════════
        # NETWORK RECONNAISSANCE
        # ═══════════════════════════════════════════════════════════
        self.register(Tool(
            name="nmap_scan",
            description="Fast or deep TCP/UDP port scanning with service detection and OS fingerprinting.",
            when_to_use="When the user mentions scanning a host, finding open ports, service detection, OS fingerprinting, or network reconnaissance on a domain/IP.",
            category="recon",
            parameters=[
                ToolParameter("target", "str", "Domain name or IP address to scan", required=True, examples=["example.com", "192.168.1.1"]),
                ToolParameter("ports", "str", "Port range or specific ports", required=False, default="top1000", examples=["80,443,8080", "1-65535", "top1000"]),
                ToolParameter("flags", "str", "Extra nmap flags", required=False, default="-sV --top-ports 1000", examples=["-sS -O", "-sV -p- -T4", "-sU"]),
            ],
            examples=[
                "nmap_scan target=example.com",
                "nmap_scan target=192.168.1.1 ports=1-65535 flags='-sV -T4'",
            ],
            timeout=120,
            run=self._run_nmap,
        ))

        self.register(Tool(
            name="dns_recon",
            description="DNS lookup, subdomain enumeration via subfinder/dig, and zone transfer checks.",
            when_to_use="When the user wants DNS info, subdomains, MX records, or to enumerate a domain's DNS footprint.",
            category="recon",
            parameters=[
                ToolParameter("domain", "str", "Domain to enumerate", required=True, examples=["example.com"]),
                ToolParameter("mode", "str", "subdomains|records|all", required=False, default="all", examples=["subdomains", "records"]),
            ],
            examples=[
                "dns_recon domain=example.com mode=subdomains",
                "dns_recon domain=example.com mode=all",
            ],
            timeout=45,
            run=self._run_dns_recon,
        ))

        self.register(Tool(
            name="whois_lookup",
            description="WHOIS domain registration lookup — registrar, creation date, nameservers, abuse contacts.",
            when_to_use="When the user wants domain ownership info, registration dates, or WHOIS data.",
            category="recon",
            parameters=[
                ToolParameter("domain", "str", "Domain to lookup", required=True, examples=["example.com"]),
            ],
            examples=["whois_lookup domain=example.com"],
            timeout=20,
            run=self._run_whois,
        ))

        # ═══════════════════════════════════════════════════════════
        # WEB APPLICATION TESTING
        # ═══════════════════════════════════════════════════════════
        self.register(Tool(
            name="web_headers",
            description="Fetch HTTP headers, status code, server banner, and security headers from a URL.",
            when_to_use="When the user wants to check a website's headers, server type, security headers (CSP, HSTS, X-Frame-Options), or basic HTTP response info.",
            category="web",
            parameters=[
                ToolParameter("url", "str", "Full URL including protocol", required=True, examples=["https://example.com", "http://target:8080/admin"]),
                ToolParameter("follow_redirects", "bool", "Follow 301/302 redirects", required=False, default=True),
            ],
            examples=[
                "web_headers url=https://example.com",
                "web_headers url=http://target:8080/api follow_redirects=false",
            ],
            timeout=20,
            run=self._run_web_headers,
        ))

        self.register(Tool(
            name="dir_enum",
            description="Directory and file enumeration using gobuster or dirsearch.",
            when_to_use="When the user wants to find hidden directories, admin panels, backup files, or sensitive endpoints on a web server.",
            category="web",
            parameters=[
                ToolParameter("url", "str", "Target URL", required=True, examples=["https://example.com"]),
                ToolParameter("wordlist", "str", "Wordlist path", required=False, default="/usr/share/wordlists/dirb/common.txt", examples=["/usr/share/seclists/Discovery/Web-Content/common.txt"]),
                ToolParameter("extensions", "str", "File extensions to check", required=False, default="php,txt,html,bak", examples=["php,txt,bak,zip,sql"]),
            ],
            examples=[
                "dir_enum url=https://example.com",
                "dir_enum url=https://target.com extensions=php,txt,bak,zip",
            ],
            timeout=120,
            run=self._run_dir_enum,
        ))

        self.register(Tool(
            name="nikto_scan",
            description="Nikto web vulnerability scanner — checks for outdated software, dangerous files, misconfigurations.",
            when_to_use="When the user wants a quick web vulnerability assessment, outdated software detection, or known misconfiguration checks on a web target.",
            category="web",
            parameters=[
                ToolParameter("host", "str", "Target host or URL", required=True, examples=["example.com", "http://192.168.1.1:8080"]),
            ],
            examples=["nikto_scan host=example.com"],
            timeout=120,
            run=self._run_nikto,
        ))

        # ═══════════════════════════════════════════════════════════
        # EXPLOITATION & PAYLOADS
        # ═══════════════════════════════════════════════════════════
        self.register(Tool(
            name="searchsploit",
            description="Search Exploit-DB for known exploits by keyword, CVE, or software name.",
            when_to_use="When the user asks about exploits, CVEs, known vulnerabilities for a specific software, or wants to find a working exploit.",
            category="exploit",
            parameters=[
                ToolParameter("query", "str", "Software name, CVE, or keyword", required=True, examples=["Apache Struts", "CVE-2024-1234", "WordPress"]),
                ToolParameter("type", "str", "Filter by exploit type", required=False, default="all", examples=["remote", "local", "webapps", "dos"]),
            ],
            examples=[
                "searchsploit query='Apache Struts'",
                "searchsploit query='CVE-2024-1234'",
            ],
            timeout=30,
            run=self._run_searchsploit,
        ))

        self.register(Tool(
            name="payload_search",
            description="Search the local PayloadsAllTheThings repository for categorized payloads.",
            when_to_use="When the user wants XSS, SQLi, RCE, LFI, XXE, SSRF, or other attack payloads for a specific vulnerability type.",
            category="exploit",
            parameters=[
                ToolParameter("category", "str", "Payload category/attack type", required=True, examples=["XSS", "SQL Injection", "LFI", "RCE", "SSRF", "XXE"]),
            ],
            examples=[
                "payload_search category=XSS",
                "payload_search category='SQL Injection'",
            ],
            timeout=10,
            run=self._run_payload_search,
        ))

        # ═══════════════════════════════════════════════════════════
        # RESEARCH & INTELLIGENCE
        # ═══════════════════════════════════════════════════════════
        self.register(Tool(
            name="ollama_research",
            description="Use the local Ollama LLM to research, summarize, explain, or generate content on any topic.",
            when_to_use="When the user asks 'what is', 'how does', 'explain', 'summarize', 'research', or needs qualitative analysis that doesn't require running a CLI tool.",
            category="research",
            parameters=[
                ToolParameter("query", "str", "What to research or explain", required=True, examples=["how does DNSSEC work", "summarize Log4Shell CVE-2021-44228"]),
                ToolParameter("system_prompt", "str", "Specialist persona for Ollama", required=False, default="You are a cybersecurity researcher. Be thorough but concise.", examples=["You are a network engineer", "You are a malware analyst"]),
            ],
            examples=[
                "ollama_research query='how does SQL injection work'",
                "ollama_research query='explain Log4Shell' system_prompt='You are a vulnerability researcher'",
            ],
            timeout=40,
            run=self._run_ollama_research,
        ))

        self.register(Tool(
            name="memory_recall",
            description="Search the bot's internal memory (KnowledgeTank + GraphRAG + long-term memory) for prior knowledge about a topic.",
            when_to_use="When the user asks 'do you remember', 'what do you know about', 'have we discussed', or when context from previous tasks would help answer.",
            category="research",
            parameters=[
                ToolParameter("query", "str", "Topic to search in memory", required=True, examples=["SQL injection techniques", "previous scan of example.com"]),
                ToolParameter("top_k", "int", "Number of results", required=False, default=5, examples=["3", "10"]),
            ],
            examples=[
                "memory_recall query='SQL injection'",
                "memory_recall query='example.com scan results' top_k=3",
            ],
            timeout=10,
            run=self._run_memory_recall,
        ))

        # ═══════════════════════════════════════════════════════════
        # CODE & AUTOMATION
        # ═══════════════════════════════════════════════════════════
        self.register(Tool(
            name="python_exec",
            description="Execute Python code safely in a restricted namespace. Can be used for data processing, scripting, or rapid prototyping.",
            when_to_use="When the user wants a script written, data processed, calculations done, or any Python automation. NOT for running shell commands directly.",
            category="code",
            parameters=[
                ToolParameter("code", "str", "Python code to execute", required=True, examples=["print('hello')", "import hashlib; print(hashlib.md5(b'test').hexdigest())"]),
            ],
            examples=[
                "python_exec code='print(2**16)'",
                "python_exec code='import json; print(json.dumps({\"a\":1}))'",
            ],
            timeout=30,
            run=self._run_python_exec,
        ))

        self.register(Tool(
            name="shell_exec",
            description="Execute arbitrary shell commands. Use with caution — only when a specific CLI tool is needed that has no dedicated wrapper.",
            when_to_use="ONLY as a fallback when no dedicated tool exists. Prefer nmap_scan, dns_recon, dir_enum, etc. Use for tools like masscan, theHarvester, or custom scripts.",
            category="system",
            dangerous=True,
            parameters=[
                ToolParameter("command", "str", "Shell command to run", required=True, examples=["masscan -p80,443 192.168.1.0/24 --rate 1000", "theHarvester -d example.com -b all"]),
                ToolParameter("timeout", "int", "Max seconds", required=False, default=60, examples=["30", "120"]),
            ],
            examples=[
                "shell_exec command='uname -a'",
                "shell_exec command='masscan -p80,443 10.0.0.0/8 --rate 1000' timeout=120",
            ],
            timeout=120,
            run=self._run_shell_exec,
        ))

        # ═══════════════════════════════════════════════════════════
        # CRYPTO & HASHING
        # ═══════════════════════════════════════════════════════════
        self.register(Tool(
            name="hash_compute",
            description="Compute MD5, SHA1, SHA256, or SHA512 hashes of strings or files.",
            when_to_use="When the user wants to hash something, verify checksums, or compute digests.",
            category="crypto",
            parameters=[
                ToolParameter("input", "str", "String to hash", required=True, examples=["password123", "sensitive_data"]),
                ToolParameter("algorithm", "str", "Hash algorithm", required=False, default="sha256", examples=["md5", "sha1", "sha256", "sha512"]),
            ],
            examples=[
                "hash_compute input='test' algorithm=sha256",
                "hash_compute input='password' algorithm=md5",
            ],
            timeout=5,
            run=self._run_hash_compute,
        ))

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        if category:
            return [t for t in self.tools.values() if t.category == category]
        return list(self.tools.values())

    def to_prompt(self, categories: Optional[List[str]] = None) -> str:
        """Format all tool descriptions for LLM consumption."""
        tools = self.list_tools()
        if categories:
            tools = [t for t in tools if t.category in categories]
        lines = ["## Available Tools", ""]
        for t in tools:
            lines.append(t.to_prompt())
            lines.append("")
        return "\n".join(lines)

    def suggest_for_task(self, task_description: str) -> List[Tool]:
        """Keyword-based fast pre-filter before LLM selection."""
        t = task_description.lower()
        scores = {}
        for name, tool in self.tools.items():
            score = 0
            # Match against when_to_use
            for word in t.split():
                if len(word) > 3 and word in tool.when_to_use.lower():
                    score += 2
                if len(word) > 3 and word in tool.description.lower():
                    score += 1
            # Category match
            if "scan" in t or "port" in t or "recon" in t:
                if tool.category == "recon": score += 3
            if "web" in t or "http" in t or "url" in t or "site" in t:
                if tool.category == "web": score += 3
            if "exploit" in t or "payload" in t or "cve" in t:
                if tool.category == "exploit": score += 3
            if "research" in t or "explain" in t or "what is" in t:
                if tool.category == "research": score += 3
            if "code" in t or "script" in t or "python" in t:
                if tool.category == "code": score += 3
            if score > 0:
                scores[name] = score
        sorted_names = sorted(scores, key=scores.get, reverse=True)
        return [self.tools[n] for n in sorted_names[:5]]

    # ═══════════════════════════════════════════════════════════
    # RUNNERS
    # ═══════════════════════════════════════════════════════════

    def _run_nmap(self, args: Dict[str, Any]) -> Dict[str, Any]:
        target = args.get("target", "")
        flags = args.get("flags", "-sV --top-ports 1000")
        ports = args.get("ports", "")
        if ports and ports != "top1000":
            flags = f"{flags} -p {ports}"
        cmd = f"nmap {flags} {target}"
        return self._shell(cmd, timeout=self.tools["nmap_scan"].timeout)

    def _run_dns_recon(self, args: Dict[str, Any]) -> Dict[str, Any]:
        domain = args.get("domain", "")
        mode = args.get("mode", "all")
        parts = []
        if mode in ("records", "all"):
            parts.append(f"dig +short {domain}")
            parts.append(f"dig +short MX {domain}")
            parts.append(f"dig +short NS {domain}")
        if mode in ("subdomains", "all"):
            parts.append(f"subfinder -d {domain} -silent 2>/dev/null | head -30 || echo 'subfinder not installed'")
        cmd = " && echo '---' && ".join(parts)
        return self._shell(cmd, timeout=self.tools["dns_recon"].timeout)

    def _run_whois(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._shell(f"whois {args.get('domain', '')} 2>/dev/null | head -40", timeout=20)

    def _run_web_headers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get("url", "")
        follow = "-L" if args.get("follow_redirects", True) else ""
        return self._shell(
            f"curl -sI {follow} -o /dev/null -w '%{{http_code}} %{{size_download}} %{{content_type}} %{{server}}\n' {url} && "
            f"curl -sI {follow} {url} 2>/dev/null | head -25",
            timeout=20
        )

    def _run_dir_enum(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get("url", "")
        wordlist = args.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        exts = args.get("extensions", "php,txt,html,bak")
        # Prefer gobuster if available
        if self._which("gobuster"):
            cmd = f"gobuster dir -u {url} -w {wordlist} -x {exts} -q -t 50 2>/dev/null | head -40"
        else:
            cmd = f"dirb {url} {wordlist} -X .{exts.replace(',', ',.')} 2>/dev/null | head -40"
        return self._shell(cmd, timeout=120)

    def _run_nikto(self, args: Dict[str, Any]) -> Dict[str, Any]:
        host = args.get("host", "")
        if not host.startswith("http"):
            host = f"http://{host}"
        return self._shell(f"nikto -h {host} -maxtime 60 2>/dev/null | head -60", timeout=120)

    def _run_searchsploit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "")
        etype = args.get("type", "all")
        flag = f"-t {etype}" if etype != "all" else ""
        return self._shell(f"searchsploit {flag} {query} 2>/dev/null | head -30", timeout=30)

    def _run_payload_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        category = args.get("category", "")
        base = os.getenv("PAYLOADS_DIR", "/home/popic/PayloadsAllTheThings")
        if not os.path.isdir(base):
            return {"success": False, "error": f"Payloads dir not found: {base}"}
        matches = []
        for root, dirs, files in os.walk(base):
            for f in files:
                if category.lower() in f.lower() or category.lower() in root.lower():
                    matches.append(os.path.join(root, f))
        # Also check top-level dirs
        folders = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)) and category.lower() in d.lower()]
        return {"success": True, "folders": folders[:10], "files": matches[:10]}

    def _run_ollama_research(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "")
        system = args.get("system_prompt", "You are a cybersecurity researcher. Be thorough but concise.")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        full = f"System: {system}\nUser: {query}\nAI:"
        try:
            r = subprocess.run(["ollama", "run", model, full], capture_output=True, text=True, timeout=40)
            return {"success": True, "result": r.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_memory_recall(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Will be injected with system memory at runtime
        return {"success": True, "result": "Use memory.search() or graphrag.query_context() from the system object."}

    def _run_python_exec(self, args: Dict[str, Any]) -> Dict[str, Any]:
        code = args.get("code", "")
        if not code:
            return {"success": False, "error": "No code provided"}
        try:
            local_ns = {}
            exec(code, {"__builtins__": __builtins__}, local_ns)
            result = local_ns.get("result", "No 'result' variable set")
            # Also capture stdout if printed
            import io, sys
            old = sys.stdout
            sys.stdout = buffer = io.StringIO()
            exec(code, {"__builtins__": __builtins__}, local_ns)
            printed = buffer.getvalue()
            sys.stdout = old
            output = printed if printed else str(result)
            return {"success": True, "result": output[:2000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_shell_exec(self, args: Dict[str, Any]) -> Dict[str, Any]:
        cmd = args.get("command", "")
        timeout = args.get("timeout", 60)
        return self._shell(cmd, timeout=timeout)

    def _run_hash_compute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import hashlib
        inp = args.get("input", "").encode()
        algo = args.get("algorithm", "sha256").lower()
        h = hashlib.new(algo, inp)
        return {"success": True, "result": h.hexdigest()}

    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════

    def _shell(self, cmd: str, timeout: int = 60) -> Dict[str, Any]:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return {
                "success": r.returncode == 0,
                "stdout": r.stdout[:4000],
                "stderr": r.stderr[:1000],
                "returncode": r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _which(self, cmd: str) -> bool:
        return subprocess.run(["which", cmd], capture_output=True).returncode == 0

