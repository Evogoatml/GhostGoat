#!/usr/bin/env bash
# ===========================================================================
# GhostGoat - One-command bootstrap installer
#
#   git clone <repo> && cd GhostGoat && ./setup.sh
#
# What this script does (in order):
#   1. System deps  — apt/brew packages (Python 3, Node, build tools)
#   2. Python venv  — isolated virtual environment
#   3. Python deps  — core packages then optional ML/embedding packages
#   4. GhostGoat    — editable install so `import ghostgoat` works
#   5. Dashboard    — npm install (skipped if Node not found)
#   6. Rust backend — cargo build (skipped if Rust not found)
#   7. .env         — creates template if not already present
# ===========================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[*]${NC} $1"; }
ok()    { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[-]${NC} $1"; exit 1; }

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║       GhostGoat Bootstrap Installer       ║"
echo "  ║   Multi-Agent Management System           ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# ------------------------------------------------------------------
# 0. System dependencies (Ubuntu/Debian only, skipped elsewhere)
# ------------------------------------------------------------------
if command -v apt-get &>/dev/null; then
    info "Detected Debian/Ubuntu — installing system packages..."
    # Delegate to the platform setup script (handles apt-get, Docker, etc.)
    if [ -f "$ROOT/setup_ghostgoat_ubuntu.sh" ]; then
        bash "$ROOT/setup_ghostgoat_ubuntu.sh" 2>&1 | grep -E "^\[|^✅|^❌|^⚠️" || true
        ok "System packages ready"
    else
        # Minimal fallback — just make sure python3-venv is present
        sudo apt-get install -y python3 python3-venv python3-pip build-essential git -q
        ok "Minimal system packages installed"
    fi
elif command -v brew &>/dev/null; then
    info "Detected macOS/Homebrew — installing system packages..."
    brew install python@3 node 2>&1 | tail -3 || true
    ok "Homebrew packages ready"
else
    info "Skipping system package install (not apt/brew — install Python 3.8+, Node 18+ manually if needed)"
fi

# ------------------------------------------------------------------
# 1. Python venv
# ------------------------------------------------------------------
info "Setting up Python virtual environment..."

if [ -d "venv" ]; then
    warn "Existing venv found — checking ownership..."
    if [ ! -w "venv" ]; then
        warn "venv not writable. Removing and recreating..."
        rm -rf venv
    fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "Created fresh venv"
else
    ok "Using existing venv"
fi

source venv/bin/activate
ok "Activated venv ($(python3 --version))"

# Upgrade pip first (avoids install errors)
pip install --upgrade pip setuptools wheel -q

# ------------------------------------------------------------------
# 2. Python dependencies (core only — no 500MB RAGFlow deps)
# ------------------------------------------------------------------
info "Installing Python dependencies..."

pip install -q \
    anthropic \
    openai \
    flask \
    flask-cors \
    fastapi \
    uvicorn \
    pydantic \
    numpy \
    pandas \
    httpx \
    aiohttp \
    websockets \
    requests \
    python-dotenv \
    pyyaml \
    colorama \
    psutil \
    networkx \
    cryptography \
    paramiko \
    redis \
    rich \
    tiktoken \
    typer \
    2>&1 | tail -3

ok "Core Python packages installed"

# Optional heavy packages (skip on low-resource machines)
info "Installing ML/embedding packages (may take a few minutes)..."

pip install -q \
    chromadb \
    sentence-transformers \
    huggingface-hub \
    scikit-learn \
    2>&1 | tail -3 || warn "Some ML packages failed (optional — system still works)"

ok "Python setup complete"

# ------------------------------------------------------------------
# 3. Install GhostGoat as editable package
# ------------------------------------------------------------------
info "Installing GhostGoat as editable package..."
pip install -e . -q 2>&1 | tail -2 || warn "Editable install had warnings (non-fatal)"
ok "GhostGoat package registered"

# ------------------------------------------------------------------
# 4. Dashboard (Node.js)
# ------------------------------------------------------------------
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    info "Node.js found ($NODE_VERSION) — installing dashboard..."
    cd "$ROOT/dashboard"
    npm install --silent 2>&1 | tail -3
    ok "Dashboard dependencies installed"
    cd "$ROOT"
else
    warn "Node.js not found — skipping dashboard setup"
    warn "Install Node.js 18+ then run: cd dashboard && npm install"
fi

# ------------------------------------------------------------------
# 5. Rust backend (optional)
# ------------------------------------------------------------------
if command -v cargo &>/dev/null; then
    info "Rust found — building backend scanner..."
    cd "$ROOT/backend"
    cargo build --release -q 2>&1 | tail -3 || warn "Rust build failed (optional)"
    ok "Rust backend built"
    cd "$ROOT"
else
    warn "Rust/cargo not found — skipping backend build (optional)"
fi

# ------------------------------------------------------------------
# 6. Create .env template if missing
# ------------------------------------------------------------------
if [ ! -f "$ROOT/.env" ]; then
    info "Creating .env template..."
    cat > "$ROOT/.env" << 'ENVEOF'
# GhostGoat Environment Configuration
# Copy this to .env and fill in your keys

# LLM Providers (at least one required)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Optional
LLM_PROVIDER=mock
MEMORY_BACKEND=memory
REDIS_URL=redis://localhost:6379
CHROMADB_PATH=./data/chromadb
ENVEOF
    ok "Created .env template — edit it with your API keys"
else
    ok ".env already exists"
fi

# ------------------------------------------------------------------
# Done
# ------------------------------------------------------------------
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Next steps:${NC}"
echo ""
echo "  1. Add your API keys:"
echo "       \$EDITOR .env"
echo ""
echo "  2. Activate the environment (if running commands manually):"
echo "       source venv/bin/activate"
echo ""
echo "  3. Start GhostGoat (API + dashboard):"
echo "       python main.py"
echo "       python main.py --api-only   # backend only"
echo "       python main.py --dash-only  # dashboard only"
echo ""
echo "  Or via make:"
echo "       make run        # starts API + dashboard"
echo "       make test       # runs test suite"
echo "       make start      # full Docker stack"
echo ""
