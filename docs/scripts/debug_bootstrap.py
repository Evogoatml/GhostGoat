#!/usr/bin/env python3
"""
GhostGoat Debug Bootstrap
=========================
Validates the entire system end-to-end and reports exactly what's broken.

Usage:
  python3 debug_bootstrap.py              # full check + auto-install missing packages
  python3 debug_bootstrap.py --smoke-only # skip full pytest (faster)
  python3 debug_bootstrap.py --check-only # read-only, no auto-fixes
  python3 debug_bootstrap.py --fix        # attempt to run setup.sh for missing deps
"""

import argparse
import importlib
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Project root — always the directory this script lives in
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Output helpers (works with or without `rich`)
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    _console = Console()

    def _print(msg="", style=""):
        _console.print(msg, style=style)

    def _header(title):
        _console.rule(f"[bold cyan]{title}[/bold cyan]")

    def _ok(label, detail=""):
        _console.print(f"  [green]PASS[/green]  {label}" + (f" — {detail}" if detail else ""))

    def _fail(label, detail=""):
        _console.print(f"  [bold red]FAIL[/bold red]  {label}" + (f" — {detail}" if detail else ""))

    def _warn(label, detail=""):
        _console.print(f"  [yellow]WARN[/yellow]  {label}" + (f" — {detail}" if detail else ""))

    def _info(label, detail=""):
        _console.print(f"  [cyan]INFO[/cyan]  {label}" + (f" — {detail}" if detail else ""))

    def _summary_table(results):
        table = Table(title="Bootstrap Summary", box=box.ROUNDED)
        table.add_column("Phase", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details")
        for r in results:
            status_str = {
                "pass": "[green]PASS[/green]",
                "fail": "[bold red]FAIL[/bold red]",
                "warn": "[yellow]WARN[/yellow]",
                "skip": "[dim]SKIP[/dim]",
            }.get(r.status, r.status)
            table.add_row(r.phase, status_str, r.detail)
        _console.print(table)

    RICH = True

except ImportError:
    RICH = False
    G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"; B = "\033[1m"; N = "\033[0m"

    def _print(msg="", style=""):
        print(msg)

    def _header(title):
        print(f"\n{C}{'─'*60}{N}")
        print(f"{C}  {title}{N}")
        print(f"{C}{'─'*60}{N}")

    def _ok(label, detail=""):
        print(f"  {G}PASS{N}  {label}" + (f" — {detail}" if detail else ""))

    def _fail(label, detail=""):
        print(f"  {R}{B}FAIL{N}  {label}" + (f" — {detail}" if detail else ""))

    def _warn(label, detail=""):
        print(f"  {Y}WARN{N}  {label}" + (f" — {detail}" if detail else ""))

    def _info(label, detail=""):
        print(f"  {C}INFO{N}  {label}" + (f" — {detail}" if detail else ""))

    def _summary_table(results):
        print(f"\n{'─'*65}")
        print(f"  {'Phase':<30}  {'Status':<6}  Details")
        print(f"{'─'*65}")
        icons = {"pass": f"{G}PASS{N}", "fail": f"{R}FAIL{N}", "warn": f"{Y}WARN{N}", "skip": "SKIP"}
        for r in results:
            print(f"  {r.phase:<30}  {icons.get(r.status, r.status):<6}  {r.detail}")
        print(f"{'─'*65}")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
@dataclass
class PhaseResult:
    phase: str
    status: str   # "pass" | "fail" | "warn" | "skip"
    detail: str = ""


@dataclass
class CheckState:
    results: List[PhaseResult] = field(default_factory=list)
    fatal: bool = False

    def add(self, result: PhaseResult):
        self.results.append(result)
        if result.status == "fail":
            self.fatal = True

    def overall(self) -> str:
        statuses = {r.status for r in self.results}
        if "fail" in statuses:
            return "fail"
        if "warn" in statuses:
            return "warn"
        return "pass"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run(cmd: List[str], capture=True, timeout=120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)


def _pip_install(*packages: str) -> bool:
    result = _run([sys.executable, "-m", "pip", "install", "-q", *packages], timeout=180)
    return result.returncode == 0


def _try_import(module: str) -> Optional[object]:
    try:
        return importlib.import_module(module)
    except ImportError:
        return None


def _check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Phase 1: Prerequisites
# ---------------------------------------------------------------------------
def phase_prerequisites(state: CheckState, args):
    _header("Phase 1 — Prerequisites")

    # Python version
    vi = sys.version_info
    if vi >= (3, 8):
        _ok(f"Python {vi.major}.{vi.minor}.{vi.micro}")
    else:
        _fail(f"Python {vi.major}.{vi.minor} — need 3.8+")
        state.add(PhaseResult("Python version", "fail", f"{vi.major}.{vi.minor} < 3.8"))
        state.fatal = True
        return  # can't continue

    state.add(PhaseResult("Python version", "pass", f"{vi.major}.{vi.minor}.{vi.micro}"))

    # pip
    try:
        r = _run([sys.executable, "-m", "pip", "--version"])
        state.add(PhaseResult("pip", "pass", r.stdout.split()[1]))
        _ok(f"pip {r.stdout.split()[1]}")
    except Exception as e:
        _fail("pip not available", str(e))
        state.add(PhaseResult("pip", "fail", str(e)))

    # Node.js
    r = _run(["node", "--version"])
    if r.returncode == 0:
        _ok(f"Node.js {r.stdout.strip()}")
        state.add(PhaseResult("Node.js", "pass", r.stdout.strip()))
    else:
        _warn("Node.js not found — dashboard won't build")
        state.add(PhaseResult("Node.js", "warn", "not found — dashboard unavailable"))

    # Rust / cargo
    r = _run(["cargo", "--version"])
    if r.returncode == 0:
        _info(f"Rust {r.stdout.strip()} (optional)")
        state.add(PhaseResult("Rust/cargo", "pass", r.stdout.strip()))
    else:
        _info("Rust/cargo not found (optional — Rust backend skipped)")
        state.add(PhaseResult("Rust/cargo", "warn", "not found — Rust backend skipped"))


# ---------------------------------------------------------------------------
# Phase 2: Environment & Project Files
# ---------------------------------------------------------------------------
def phase_environment(state: CheckState, args):
    _header("Phase 2 — Environment & Project Files")

    # .env file
    env_path = ROOT / ".env"
    if env_path.exists():
        _ok(".env exists")
        state.add(PhaseResult(".env", "pass"))
    else:
        if not args.check_only:
            env_path.write_text(
                "# GhostGoat environment — fill in your API keys\n"
                "LLM_PROVIDER=mock\n"
                "MEMORY_BACKEND=memory\n"
                "REDIS_URL=redis://localhost:6379\n"
                "CHROMADB_PATH=./data/chromadb\n"
                "ANTHROPIC_API_KEY=\n"
                "OPENAI_API_KEY=\n"
            )
            _warn(".env was missing — created template")
            state.add(PhaseResult(".env", "warn", "created template — add your API keys"))
        else:
            _warn(".env missing (--check-only: not created)")
            state.add(PhaseResult(".env", "warn", "missing — run without --check-only to create"))

    # data/ directory writable
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    test_file = data_dir / ".bootstrap_write_test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
        _ok("data/ directory writable")
        state.add(PhaseResult("data/ writable", "pass"))
    except OSError as e:
        _fail("data/ not writable", str(e))
        state.add(PhaseResult("data/ writable", "fail", str(e)))

    # requirements.txt present
    req_path = ROOT / "requirements.txt"
    if req_path.exists():
        _ok("requirements.txt present")
        state.add(PhaseResult("requirements.txt", "pass"))
    else:
        _warn("requirements.txt not found")
        state.add(PhaseResult("requirements.txt", "warn", "missing"))

    # dashboard/node_modules
    node_modules = ROOT / "dashboard" / "node_modules"
    if node_modules.exists():
        _ok("dashboard/node_modules installed")
        state.add(PhaseResult("dashboard deps", "pass"))
    else:
        _warn("dashboard/node_modules missing — run: cd dashboard && npm install")
        state.add(PhaseResult("dashboard deps", "warn", "npm install not run"))


# ---------------------------------------------------------------------------
# Phase 3: Python Package Installation
# ---------------------------------------------------------------------------
REQUIRED_PACKAGES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("httpx", "httpx"),
    ("anthropic", "anthropic"),
    ("openai", "openai"),
    ("redis", "redis"),
    ("yaml", "pyyaml"),
    ("dotenv", "python-dotenv"),
    ("psutil", "psutil"),
    ("networkx", "networkx"),
    ("cryptography", "cryptography"),
    ("paramiko", "paramiko"),
    ("colorama", "colorama"),
    ("requests", "requests"),
    ("aiohttp", "aiohttp"),
    ("websockets", "websockets"),
    ("numpy", "numpy"),
]

OPTIONAL_PACKAGES = [
    ("chromadb", "chromadb"),
    ("sentence_transformers", "sentence-transformers"),
    ("sklearn", "scikit-learn"),
]


def phase_packages(state: CheckState, args):
    _header("Phase 3 — Python Package Check")

    missing_required = []
    missing_optional = []

    for module, pip_name in REQUIRED_PACKAGES:
        if _try_import(module) is not None:
            _ok(pip_name)
        else:
            _fail(f"{pip_name} not installed")
            missing_required.append(pip_name)

    for module, pip_name in OPTIONAL_PACKAGES:
        if _try_import(module) is not None:
            _ok(f"{pip_name} (optional)")
        else:
            _warn(f"{pip_name} not installed (optional)")
            missing_optional.append(pip_name)

    if missing_required and not args.check_only:
        _print()
        _info(f"Installing {len(missing_required)} missing required package(s)...")
        if _pip_install(*missing_required):
            _ok(f"Installed: {', '.join(missing_required)}")
            state.add(PhaseResult("Required packages", "pass", f"auto-installed: {', '.join(missing_required)}"))
        else:
            _fail(f"Failed to install: {', '.join(missing_required)}")
            state.add(PhaseResult("Required packages", "fail", f"could not install: {', '.join(missing_required)}"))
    elif missing_required:
        state.add(PhaseResult("Required packages", "fail",
                               f"missing: {', '.join(missing_required)} — run: pip install {' '.join(missing_required)}"))
    else:
        state.add(PhaseResult("Required packages", "pass", "all present"))

    if missing_optional:
        state.add(PhaseResult("Optional packages", "warn", f"missing: {', '.join(missing_optional)}"))
    else:
        state.add(PhaseResult("Optional packages", "pass", "all present"))


# ---------------------------------------------------------------------------
# Phase 4: Core Module Imports
# ---------------------------------------------------------------------------
CORE_IMPORTS = [
    # config/
    ("config.unified_config", "config/ — unified config"),
    # frameworks/
    ("frameworks.llm.multi_llm", "frameworks/ — LLM framework"),
    ("frameworks.monitoring.monitoring", "frameworks/ — monitoring"),
    # core/
    ("core.ghostgoat_core", "core/ — GhostGoat core"),
    ("core.build_loop", "core/ — BuildLoop"),
    ("core.self_aware_loop", "core/ — SelfAwareLoop"),
    ("core.service_registry", "core/ — ServiceRegistry"),
    ("core.task_handler", "core/ — TaskHandler"),
    ("core.governance.decision_governor", "core/ — DecisionGovernor"),
    # api/
    ("api.server", "api/ — API server"),
    # agents/
    ("agents.base", "agents/ — base agent"),
    ("agents.nanoagent", "agents/ — nanoagent"),
    # tools/
    ("tools.registry", "tools/ — tool registry"),
    # integrations/
    ("integrations.universal_api_client", "integrations/ — universal API client"),
    # ACS_SYSTEM/
    ("ACS_SYSTEM.advanced_ciphers", "ACS_SYSTEM/ — ciphers"),
    ("ACS_SYSTEM.crystal_crypto", "ACS_SYSTEM/ — crystal crypto"),
    # utils
    ("utils", "utils.py — utilities"),
]


def phase_imports(state: CheckState, args):
    _header("Phase 4 — Core Module Imports")

    failures = []
    for module, label in CORE_IMPORTS:
        # Reload in case packages were just installed
        if module in sys.modules:
            del sys.modules[module]
        mod = _try_import(module)
        if mod is not None:
            _ok(label, module)
        else:
            # Capture real error
            try:
                importlib.import_module(module)
            except Exception as e:
                _fail(label, f"{module} → {e}")
                failures.append(f"{module}: {e}")

    if failures:
        state.add(PhaseResult("Core imports", "fail", f"{len(failures)} module(s) failed"))
    else:
        state.add(PhaseResult("Core imports", "pass", "all modules importable"))


# ---------------------------------------------------------------------------
# Phase 5: Folder & File Integrity Scan
# ---------------------------------------------------------------------------
REQUIRED_DIRS = [
    "config", "core", "api", "agents", "tools", "frameworks",
    "integrations", "ACS_SYSTEM", "applications", "tests", "data",
]
REQUIRED_FILES = [
    "main.py", "requirements.txt", "Makefile", "setup.sh",
    "config/unified_config.py", "core/ghostgoat_core.py",
    "api/server.py", "tests/smoke_test.py",
]
OPTIONAL_BINARIES = [
    ("backend/target/release/ghostgoat-backend", "Rust backend binary"),
]
OPTIONAL_DIRS = [
    ("crypto", "crypto keys directory"),
    ("keys", "keys directory"),
    ("dashboard/node_modules", "dashboard npm deps"),
]


def phase_integrity(state: CheckState, args):
    _header("Phase 5 — Folder & File Integrity")

    failures = []
    for d in REQUIRED_DIRS:
        path = ROOT / d
        if path.is_dir():
            _ok(f"{d}/")
        else:
            _fail(f"{d}/ — directory missing!")
            failures.append(d)

    for f in REQUIRED_FILES:
        path = ROOT / f
        if path.is_file():
            _ok(f)
        else:
            _fail(f"{f} — file missing!")
            failures.append(f)

    for rel, label in OPTIONAL_BINARIES:
        path = ROOT / rel
        if path.is_file():
            _ok(f"{label}: {rel}")
        else:
            _info(f"{label} not built (run: cd backend && cargo build --release)")

    for rel, label in OPTIONAL_DIRS:
        path = ROOT / rel
        if path.exists():
            _ok(f"{label}: {rel}/")
        else:
            _warn(f"{label} missing: {rel}/")

    if failures:
        state.add(PhaseResult("Folder/file integrity", "fail",
                               f"{len(failures)} missing: {', '.join(failures)}"))
    else:
        state.add(PhaseResult("Folder/file integrity", "pass",
                               f"{len(REQUIRED_DIRS)} dirs, {len(REQUIRED_FILES)} files verified"))


# ---------------------------------------------------------------------------
# Phase 6: Configuration Validation
# ---------------------------------------------------------------------------
def phase_config(state: CheckState, args):
    _header("Phase 6 — Configuration")

    try:
        # Force fresh load
        for mod in list(sys.modules.keys()):
            if "unified_config" in mod:
                del sys.modules[mod]

        from config.unified_config import init_config
        cfg = init_config()

        assert cfg is not None, "init_config() returned None"
        assert hasattr(cfg, "llm"), "config missing .llm"
        assert hasattr(cfg, "memory"), "config missing .memory"

        _ok(f"LLM provider: {cfg.llm.provider}")
        _ok(f"Memory backend: {cfg.memory.backend}")
        _ok(f"Base path: {cfg.base_path}")

        if not Path(cfg.base_path).exists():
            _warn(f"base_path does not exist: {cfg.base_path}")
            state.add(PhaseResult("Config", "warn", f"base_path missing: {cfg.base_path}"))
        else:
            state.add(PhaseResult("Config", "pass", f"provider={cfg.llm.provider}, memory={cfg.memory.backend}"))

    except Exception as e:
        _fail("Configuration failed to load", str(e))
        state.add(PhaseResult("Config", "fail", str(e)))


# ---------------------------------------------------------------------------
# Phase 6: Optional Service Connectivity
# ---------------------------------------------------------------------------
def phase_services(state: CheckState, args):
    _header("Phase 7 — Optional Service Connectivity")

    # Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    host = "localhost"
    port = 6379
    try:
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
    except Exception:
        pass

    if _check_port_open(host, port):
        _ok(f"Redis reachable at {host}:{port}")
        state.add(PhaseResult("Redis", "pass", f"{host}:{port}"))
    else:
        _warn(f"Redis not reachable at {host}:{port} (optional — memory backend used)")
        state.add(PhaseResult("Redis", "warn", f"{host}:{port} not reachable"))

    # ChromaDB HTTP (if running as service)
    if _check_port_open("localhost", 8000, timeout=1.0):
        _ok("ChromaDB service reachable at localhost:8000")
        state.add(PhaseResult("ChromaDB", "pass", "localhost:8000"))
    else:
        _info("ChromaDB HTTP not running (will use embedded mode)")
        state.add(PhaseResult("ChromaDB", "warn", "HTTP service not running — embedded mode"))


# ---------------------------------------------------------------------------
# Phase 7: Test Suite
# ---------------------------------------------------------------------------
def phase_tests(state: CheckState, args):
    _header("Phase 8 — Test Suite")

    pytest_args = [sys.executable, "-m", "pytest", "tests/", "--tb=short", "-q"]

    if args.smoke_only:
        pytest_args += ["-m", "smoke", "--ignore=tests/test_api_server.py"]
        label = "Smoke tests"
    else:
        label = "Full test suite"

    _info(f"Running: {' '.join(pytest_args[2:])}")
    t0 = time.time()
    result = subprocess.run(pytest_args, capture_output=False, text=True, cwd=str(ROOT))
    elapsed = time.time() - t0

    if result.returncode == 0:
        _ok(f"{label} passed", f"{elapsed:.1f}s")
        state.add(PhaseResult(label, "pass", f"{elapsed:.1f}s"))
    else:
        _fail(f"{label} had failures", f"exit code {result.returncode}")
        state.add(PhaseResult(label, "fail", f"exit code {result.returncode} — see output above"))


# ---------------------------------------------------------------------------
# Phase 8: API Server Startup Check
# ---------------------------------------------------------------------------
def phase_api_startup(state: CheckState, args):
    _header("Phase 9 — API Server Startup")

    _info("Starting API server for health check (5s)...")
    proc = subprocess.Popen(
        [sys.executable, "main.py", "--api-only"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )

    try:
        # Wait for the server to bind
        deadline = time.time() + 8
        ready = False
        while time.time() < deadline:
            if _check_port_open("localhost", 8420):
                ready = True
                break
            time.sleep(0.5)

        if not ready:
            _fail("API server did not bind on port 8420 within 8s")
            state.add(PhaseResult("API startup", "fail", "port 8420 not reachable after 8s"))
            return

        # Hit the health endpoint
        import urllib.request
        try:
            with urllib.request.urlopen("http://localhost:8420/api/health", timeout=3) as resp:
                body = resp.read().decode()
                _ok("/api/health responded", body[:80])
                state.add(PhaseResult("API startup", "pass", "/api/health OK"))
        except Exception as e:
            _warn(f"/api/health error: {e} — server running but health endpoint issue")
            state.add(PhaseResult("API startup", "warn", f"/api/health: {e}"))

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="GhostGoat Debug Bootstrap")
    parser.add_argument("--smoke-only", action="store_true", help="Run smoke tests only (faster)")
    parser.add_argument("--check-only", action="store_true", help="Read-only mode — no auto-fixes or installs")
    parser.add_argument("--fix", action="store_true", help="Run setup.sh to rebuild environment from scratch")
    parser.add_argument("--skip-api", action="store_true", help="Skip API startup check")
    args = parser.parse_args()

    _print()
    _print("  ╔══════════════════════════════════════════╗")
    _print("  ║   GhostGoat Debug Bootstrap              ║")
    _print("  ║   Validates the full system end-to-end   ║")
    _print("  ╚══════════════════════════════════════════╝")
    _print()

    if args.fix and not args.check_only:
        _header("Pre-flight: Running setup.sh")
        result = subprocess.run(["bash", "setup.sh"], cwd=str(ROOT))
        if result.returncode != 0:
            _warn("setup.sh exited with non-zero — continuing anyway")

    state = CheckState()

    phases = [
        phase_prerequisites,
        phase_environment,
        phase_packages,
        phase_imports,
        phase_integrity,
        phase_config,
        phase_services,
        phase_tests,
    ]

    if not args.skip_api:
        phases.append(phase_api_startup)

    for phase_fn in phases:
        phase_fn(state, args)
        if state.fatal and phase_fn is phase_prerequisites:
            _fail("Fatal prerequisite failure — cannot continue")
            break
        _print()

    # Summary
    _header("Summary")
    _summary_table(state.results)
    _print()

    overall = state.overall()
    if overall == "pass":
        _print("  [green]All checks passed — GhostGoat is healthy.[/green]" if RICH
               else f"  \033[92mAll checks passed — GhostGoat is healthy.\033[0m")
        _print()
        _print("  Next steps:")
        _print("    python main.py --api-only    # start API")
        _print("    python main.py               # start API + dashboard")
        _print("    make test                    # run full test suite")
    elif overall == "warn":
        _print("  [yellow]Checks passed with warnings — review items above.[/yellow]" if RICH
               else f"  \033[93mChecks passed with warnings — review items above.\033[0m")
    else:
        _print("  [bold red]Failures detected — fix the FAIL items above.[/bold red]" if RICH
               else f"  \033[91mFailures detected — fix the FAIL items above.\033[0m")
        _print()
        _print("  Quick fixes:")
        _print("    pip install -r requirements.txt    # install all Python deps")
        _print("    python debug_bootstrap.py --fix    # run full setup.sh + re-check")

    _print()
    return 0 if overall in ("pass", "warn") else 1


if __name__ == "__main__":
    sys.exit(main())
