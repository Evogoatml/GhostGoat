"""
Tool registry — agents call tools through here.
Each tool is a function that returns a ToolResult.
"""

import os
import hashlib
import socket
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None


class ToolRegistry:
    """
    Central registry of tools available to agents.
    Tools are plain functions wrapped with a name.
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._register_builtins()

    def register(self, name: str, func: Callable):
        self._tools[name] = func
        logger.debug("Tool registered: %s", name)

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        func = self._tools.get(name)
        if not func:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        try:
            output = func(**kwargs)
            return ToolResult(success=True, output=output)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return ToolResult(success=False, error=str(e))

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    # ── Built-in tools ────────────────────────────────────────────

    def _register_builtins(self):
        self.register("list_directory", self._list_directory)
        self.register("read_file", self._read_file)
        self.register("write_file", self._write_file)
        self.register("hash", self._hash)
        self.register("port_scan", self._port_scan)
        self.register("http_request", self._http_request)
        self.register("system_info", self._system_info)
        self.register("web_search", self._web_search)
        self.register("fetch_url", self._fetch_url)
        self.register("execute_python", self._execute_python)
        self.register("create_workspace_file", self._create_workspace_file)
        self.register("remember", self._remember)
        self.register("recall", self._recall)
        self.register("set_api_key", self._set_api_key)
        self.register("list_api_keys", self._list_api_keys)
        # HuggingFace + GitHub discovery & integration
        self.register("search_hf_models", self._search_hf_models)
        self.register("search_hf_datasets", self._search_hf_datasets)
        self.register("get_hf_model_info", self._get_hf_model_info)
        self.register("download_hf_model", self._download_hf_model)
        self.register("search_github", self._search_github)
        self.register("clone_github_repo", self._clone_github_repo)
        self.register("install_package", self._install_package)
        self.register("install_requirements", self._install_requirements)
        self.register("memory_stats", self._memory_stats)
        self.register("memory_clear", self._memory_clear)

    # ── Real capability tools ─────────────────────────────────────────

    @staticmethod
    def _web_search(query: str, max_results: int = 6, **_) -> list:
        """Search the web via DuckDuckGo and return title/url/snippet list."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                return [
                    {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                    for r in ddgs.text(query, max_results=max_results)
                ]
        except Exception as e:
            logger.warning("[tool:web_search] DuckDuckGo failed (%s), trying requests fallback", e)
            import urllib.parse, urllib.request
            q = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={q}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            import re
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
            titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.S)
            return [{"title": re.sub(r'<[^>]+>', '', t), "snippet": re.sub(r'<[^>]+>', '', s), "url": ""}
                    for t, s in zip(titles[:max_results], snippets[:max_results])]

    @staticmethod
    def _fetch_url(url: str, **_) -> str:
        """Fetch a URL and return readable text (strips HTML tags)."""
        import urllib.request, re
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # Strip scripts/styles then tags
        html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:8000]

    @staticmethod
    def _execute_python(code: str, timeout: int = 15, **_) -> dict:
        """Execute Python code in a subprocess sandbox. Returns stdout/stderr."""
        import subprocess, tempfile
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            fname = f.name
        try:
            result = subprocess.run(
                ["python3", fname],
                capture_output=True, text=True, timeout=timeout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            return {
                "stdout": result.stdout[:4000],
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"Timed out after {timeout}s", "returncode": -1}
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    @staticmethod
    def _create_workspace_file(filename: str, content: str, **_) -> str:
        """Write a file into GhostGoat's workspace directory."""
        workspace = Path(os.path.expanduser("~")) / "ghostgoat_workspace"
        workspace.mkdir(exist_ok=True)
        # Sanitise filename (no directory traversal)
        safe = Path(filename).name
        if not safe:
            safe = "output.txt"
        dest = workspace / safe
        dest.write_text(content)
        return f"Created {dest} ({len(content)} chars)"

    # Simple flat-file memory (survives restarts)
    _MEMORY_FILE = Path(os.path.expanduser("~")) / ".ghostgoat_memory.json"

    @classmethod
    def _remember(cls, key: str, value: str, **_) -> str:
        """Store a key-value memory that persists across restarts."""
        import json
        mem: dict = {}
        if cls._MEMORY_FILE.exists():
            try:
                mem = json.loads(cls._MEMORY_FILE.read_text())
            except Exception:
                pass
        mem[key] = value
        cls._MEMORY_FILE.write_text(json.dumps(mem, indent=2))
        return f"Remembered: {key} = {value}"

    # Known API key environment variable names
    _API_KEY_MAP = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "huggingface": "HUGGINGFACE_API_TOKEN",
        "hf": "HUGGINGFACE_API_TOKEN",
        "telegram": "TELEGRAM_BOT_TOKEN",
        "serp": "SERP_API_KEY",
        "serpapi": "SERP_API_KEY",
        "stability": "STABILITY_API_KEY",
        "replicate": "REPLICATE_API_TOKEN",
        "groq": "GROQ_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "cohere": "COHERE_API_KEY",
        "elevenlabs": "ELEVENLABS_API_KEY",
    }

    _ENV_FILE = Path(os.path.expanduser("~")) / "GhostGoat" / ".env"

    @classmethod
    def _set_api_key(cls, service: str, key: str, **_) -> str:
        """Write an API key to .env and reload it into the running process."""
        # Resolve env var name
        svc_lower = service.lower().replace(" ", "").replace("_", "").replace("-", "")
        env_var = cls._API_KEY_MAP.get(svc_lower)
        if not env_var:
            # Accept raw env var name (e.g. OPENAI_API_KEY)
            if service.isupper() and "_" in service:
                env_var = service
            else:
                known = ", ".join(cls._API_KEY_MAP.keys())
                return f"Unknown service '{service}'. Known: {known}. Or pass the exact env var name."

        # Find .env file (walk up from here)
        env_file = cls._ENV_FILE
        for candidate in [
            Path("/home/user/GhostGoat/.env"),
            Path(os.path.expanduser("~/GhostGoat/.env")),
            Path(__file__).resolve().parent.parent / ".env",
        ]:
            if candidate.exists():
                env_file = candidate
                break

        # Read existing .env
        lines: list = []
        if env_file.exists():
            lines = env_file.read_text().splitlines()

        # Update or append the key
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{env_var}=") or line.startswith(f"{env_var} ="):
                lines[i] = f"{env_var}={key}"
                updated = True
                break
        if not updated:
            lines.append(f"{env_var}={key}")

        env_file.write_text("\n".join(lines) + "\n")

        # Reload into current process immediately
        os.environ[env_var] = key

        # Re-initialise LLM controller so it picks up the new key
        try:
            from core.controllers.llm_controller import LLMController
            LLMController._instance = None
            new_llm = LLMController()
            logger.info("[tool:set_api_key] LLM controller reloaded. providers=%s", new_llm._provider_names)
            provider_info = f" Active LLM providers: {new_llm._provider_names}"
        except Exception as e:
            provider_info = f" (LLM reload failed: {e})"

        return f"✅ {env_var} saved to {env_file} and loaded into this session.{provider_info}"

    @classmethod
    def _list_api_keys(cls, **_) -> str:
        """Show which API keys are configured (masked)."""
        results = []
        env_file = None
        for candidate in [
            Path("/home/user/GhostGoat/.env"),
            Path(os.path.expanduser("~/GhostGoat/.env")),
            Path(__file__).resolve().parent.parent / ".env",
        ]:
            if candidate.exists():
                env_file = candidate
                break

        env_vals: dict = {}
        if env_file:
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_vals[k.strip()] = v.strip()

        for svc, var in sorted(cls._API_KEY_MAP.items(), key=lambda x: x[1]):
            val = env_vals.get(var) or os.getenv(var, "")
            status = f"✅ set ({val[:6]}...)" if val and len(val) > 6 else ("⚠️ set (short?)" if val else "❌ not set")
            results.append(f"{var}: {status}")

        return "\n".join(results)

    @classmethod
    def _recall(cls, key: str = "", **_) -> str:
        """Retrieve stored memories. Pass key='' to list all."""
        import json
        if not cls._MEMORY_FILE.exists():
            return "No memories stored yet."
        try:
            mem = json.loads(cls._MEMORY_FILE.read_text())
        except Exception:
            return "Memory store unreadable."
        if key:
            return str(mem.get(key, f"No memory for key '{key}'"))
        return json.dumps(mem, indent=2) if mem else "Memory is empty."

    @staticmethod
    def _list_directory(path: str = ".", recursive: bool = False, **_) -> list:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        if recursive:
            return [str(f) for f in p.rglob("*") if f.is_file()]
        return [str(f) for f in p.iterdir()]

    @staticmethod
    def _read_file(path: str, **_) -> str:
        return Path(path).read_text(errors="replace")[:50000]

    @staticmethod
    def _write_file(path: str, content: str, **_) -> str:
        Path(path).write_text(content)
        return f"Written {len(content)} bytes to {path}"

    @staticmethod
    def _hash(text: str = "", algorithm: str = "sha256", **_) -> dict:
        h = hashlib.new(algorithm, text.encode())
        return {"algorithm": algorithm, "hash": h.hexdigest()}

    @staticmethod
    def _port_scan(host: str = "localhost", ports: list = None, **_) -> dict:
        ports = ports or [80, 443, 22, 8080]
        open_ports = []
        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex((host, port)) == 0:
                        open_ports.append(port)
            except Exception:
                pass
        return {"host": host, "scanned": ports, "open_ports": open_ports}

    @staticmethod
    def _http_request(url: str, method: str = "GET", **_) -> dict:
        import urllib.request
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {
                "status_code": resp.status,
                "headers": dict(resp.headers),
                "body_length": len(resp.read()),
            }

    @staticmethod
    def _system_info(**_) -> dict:
        import platform
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": mem.percent,
                "memory_total_mb": round(mem.total / 1024 / 1024),
            }
        except ImportError:
            return {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cpu_count": os.cpu_count(),
            }


    # ── HuggingFace tools ─────────────────────────────────────────────

    @staticmethod
    def _search_hf_models(query: str, task: str = "", limit: int = 8, **_) -> list:
        """Search HuggingFace Hub for models. task e.g. text-generation, image-classification."""
        import urllib.request, json as _json, urllib.parse
        params = {"search": query, "limit": limit, "full": "false", "config": "false"}
        if task:
            params["pipeline_tag"] = task
        url = "https://huggingface.co/api/models?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "GhostGoat/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            models = _json.loads(resp.read())
        results = []
        for m in models:
            results.append({
                "id": m.get("id", ""),
                "task": m.get("pipeline_tag", ""),
                "downloads": m.get("downloads", 0),
                "likes": m.get("likes", 0),
                "tags": m.get("tags", [])[:6],
                "url": f"https://huggingface.co/{m.get('id', '')}",
            })
        return results

    @staticmethod
    def _search_hf_datasets(query: str, limit: int = 8, **_) -> list:
        """Search HuggingFace Hub for datasets."""
        import urllib.request, json as _json, urllib.parse
        params = {"search": query, "limit": limit, "full": "false"}
        url = "https://huggingface.co/api/datasets?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "GhostGoat/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            datasets = _json.loads(resp.read())
        results = []
        for d in datasets:
            results.append({
                "id": d.get("id", ""),
                "downloads": d.get("downloads", 0),
                "likes": d.get("likes", 0),
                "tags": d.get("tags", [])[:6],
                "url": f"https://huggingface.co/datasets/{d.get('id', '')}",
            })
        return results

    @staticmethod
    def _get_hf_model_info(model_id: str, **_) -> dict:
        """Get detailed info about a specific HuggingFace model."""
        import urllib.request, json as _json
        url = f"https://huggingface.co/api/models/{model_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "GhostGoat/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
        return {
            "id": data.get("id"),
            "task": data.get("pipeline_tag"),
            "downloads": data.get("downloads"),
            "likes": data.get("likes"),
            "tags": data.get("tags", []),
            "library": data.get("library_name"),
            "model_card": (data.get("cardData") or {}).get("license", ""),
            "siblings": [f["rfilename"] for f in data.get("siblings", [])[:10]],
            "url": f"https://huggingface.co/{model_id}",
        }

    @staticmethod
    def _download_hf_model(model_id: str, cache_dir: str = "", **_) -> str:
        """Download / cache a HuggingFace model using huggingface_hub."""
        from huggingface_hub import snapshot_download
        kwargs = {}
        if cache_dir:
            kwargs["local_dir"] = cache_dir
        token = os.getenv("HUGGINGFACE_API_TOKEN", "") or os.getenv("HF_TOKEN", "")
        if token:
            kwargs["token"] = token
        path = snapshot_download(model_id, **kwargs)
        return f"Downloaded to: {path}"

    # ── GitHub tools ──────────────────────────────────────────────────

    @staticmethod
    def _search_github(query: str, language: str = "", sort: str = "stars",
                       limit: int = 8, **_) -> list:
        """Search GitHub repositories. sort: stars | forks | updated."""
        import urllib.request, json as _json, urllib.parse
        q = query
        if language:
            q += f" language:{language}"
        params = {"q": q, "sort": sort, "order": "desc", "per_page": limit}
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(params)
        headers = {"User-Agent": "GhostGoat/1.0", "Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())
        results = []
        for r in data.get("items", []):
            results.append({
                "name": r["full_name"],
                "description": r.get("description", ""),
                "stars": r["stargazers_count"],
                "language": r.get("language", ""),
                "url": r["html_url"],
                "clone_url": r["clone_url"],
                "topics": r.get("topics", [])[:6],
            })
        return results

    @staticmethod
    def _clone_github_repo(url: str, dest: str = "", branch: str = "", **_) -> str:
        """Clone a GitHub repo into ~/ghostgoat_workspace/ (or a specified path)."""
        import subprocess as _sp
        workspace = Path(os.path.expanduser("~")) / "ghostgoat_workspace"
        workspace.mkdir(exist_ok=True)
        if not dest:
            repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
            dest = str(workspace / repo_name)
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["-b", branch]
        cmd += [url, dest]
        result = _sp.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return f"Cloned to {dest}"
        return f"Clone failed: {result.stderr[:500]}"

    # ── Package management ────────────────────────────────────────────

    @staticmethod
    def _install_package(package: str, **_) -> str:
        """pip install a package and report the result."""
        import subprocess as _sp
        result = _sp.run(
            ["pip", "install", package, "--quiet"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return f"Installed {package} successfully."
        return f"Install failed:\n{result.stderr[:800]}"

    @staticmethod
    def _install_requirements(repo_path: str, **_) -> str:
        """pip install -r requirements.txt from a cloned repo."""
        import subprocess as _sp
        req_file = Path(repo_path) / "requirements.txt"
        if not req_file.exists():
            # Try setup.py or pyproject.toml
            for alt in ["setup.py", "pyproject.toml"]:
                if (Path(repo_path) / alt).exists():
                    result = _sp.run(
                        ["pip", "install", "-e", repo_path, "--quiet"],
                        capture_output=True, text=True, timeout=180,
                    )
                    return (f"Installed via {alt}: OK" if result.returncode == 0
                            else f"Failed: {result.stderr[:500]}")
            return f"No requirements.txt found in {repo_path}"
        result = _sp.run(
            ["pip", "install", "-r", str(req_file), "--quiet"],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode == 0:
            return f"Installed requirements from {req_file}"
        return f"Install failed:\n{result.stderr[:800]}"

    # ── Memory management tools ───────────────────────────────────────

    @staticmethod
    def _memory_stats(user_id: str = "default", **_) -> dict:
        """Return memory usage stats for a user."""
        try:
            from core.memory.conversation_memory import conversation_memory
            return conversation_memory.stats(user_id)
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def _memory_clear(user_id: str = "default", **_) -> str:
        """Wipe all stored memory for a user. Use with care."""
        try:
            from core.memory.conversation_memory import conversation_memory
            conversation_memory.clear(user_id)
            return f"Memory cleared for user {user_id}."
        except Exception as e:
            return f"Clear failed: {e}"


# Global singleton
registry = ToolRegistry()
