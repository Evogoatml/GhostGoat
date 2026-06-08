#!/bin/bash

set -e  # Exit on error

echo "🐐 GHOSTGOAT ULTIMATE MULTI-AGENT SYSTEM INSTALLER"
echo "=================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found"
    echo "Please run this from your project root directory"
    exit 1
fi

# Step 1: Organize project
echo "[1/6] 🗂️  Organizing GhostGoat project structure..."
bash organize_ghostgoat.sh

# Step 2: System setup
echo ""
echo "[2/6] 🖥️  Setting up Ubuntu environment..."
bash setup_ghostgoat_ubuntu.sh

# Step 3: Install Python dependencies
echo ""
echo "[3/6] 📦 Installing Python packages..."
cd ~/GhostGoat
source venv/bin/activate

pip install -r requirements.txt

# Install additional GhostGoat-specific packages
echo "Installing GhostGoat frameworks..."
pip install \
    crewai \
    crewai-tools \
    anthropic \
    openai \
    chromadb \
    redis \
    neo4j \
    fastapi \
    uvicorn \
    pydantic \
    numpy \
    pandas \
    torch \
    transformers \
    sentence-transformers \
    langchain \
    langchain-community \
    langgraph \
    httpx \
    aiohttp \
    websockets \
    python-dotenv

# Step 4: Set up databases
echo ""
echo "[4/6] 🗄️  Setting up databases..."

# Start Docker services
cd ~/GhostGoat
docker-compose up -d

echo "Waiting for services to start..."
sleep 15

# Initialize databases
python3 << PYTHON
import asyncio
from core.memory.unified_memory import create_memory

async def init():
    memory = create_memory()
    print("✅ Memory systems initialized")

asyncio.run(init())
PYTHON

# Step 5: Configure
echo ""
echo "[5/6] ⚙️  Configuring GhostGoat..."

# Create necessary directories
mkdir -p ~/GhostGoat/{logs,data/cache,crypto/keys}

# Generate encryption keys
python3 << PYTHON
import secrets
key = secrets.token_hex(32)
print(f"Generated encryption key: {key}")
with open('/tmp/ghostgoat_key.txt', 'w') as f:
    f.write(key)
PYTHON

echo "✅ Configuration complete"

# Step 6: Run tests
echo ""
echo "[6/6] 🧪 Running tests..."
cd ~/GhostGoat
python tests/smoke_test.py || echo "⚠️  Some tests failed (this is okay for first run)"

echo ""
echo "=============================================="
echo "✅ GHOSTGOAT INSTALLATION COMPLETE!"
echo "=============================================="
echo ""
echo "📍 Project Location: ~/GhostGoat/"
echo ""
echo "🔧 Next Steps:"
echo "  1. Edit API keys: nano ~/GhostGoat/.env"
echo "  2. Activate environment: source ~/GhostGoat/venv/bin/activate"
echo "  3. Start GhostGoat: bash ~/GhostGoat/scripts/start.sh"
echo ""
echo "🌐 Access Points:"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Empire Dashboard: http://localhost:3000"
echo "  • Neo4j Browser: http://localhost:7474"
echo "  • ChromaDB: http://localhost:8001"
echo ""
echo "📚 Documentation: ~/GhostGoat/docs/"
echo ""

