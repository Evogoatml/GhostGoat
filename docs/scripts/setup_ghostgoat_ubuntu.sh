#!/bin/bash

echo "🐐 Setting up Ubuntu for GhostGoat System..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.11 (or use existing Python 3)
echo "🐍 Installing Python..."
sudo apt-get install -y python3 python3-venv python3-pip python3-dev

# Install build tools
echo "🔧 Installing build tools..."
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    tree \
    htop \
    software-properties-common

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
echo "🐳 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Install Node.js (for Empire frontend)
echo "📦 Installing Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "✅ Node.js installed"
else
    echo "✅ Node.js already installed"
fi

# Install Redis
echo "📦 Installing Redis..."
if ! command -v redis-server &> /dev/null; then
    sudo apt-get install -y redis-server
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
    echo "✅ Redis installed"
else
    echo "✅ Redis already installed"
fi

# Install system libraries
echo "📦 Installing system libraries..."
sudo apt-get install -y \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpq-dev

echo ""
echo "✅ System dependencies installed!"
echo ""

# Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate and upgrade pip
source venv/bin/activate
pip install --upgrade pip setuptools wheel

echo "✅ GhostGoat Python environment ready!"

# Create .env file
echo "📝 Creating .env configuration file..."
cat > .env << 'ENVFILE'
# GhostGoat Configuration
GHOSTGOAT_ENV=production
GHOSTGOAT_DEBUG=false

# LLM API Keys (EDIT THESE!)
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Database URLs
REDIS_URL=redis://localhost:6379
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=ghostgoat123
CHROMADB_URL=http://localhost:8001

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Agent Configuration
MAX_AGENTS=50
AGENT_TIMEOUT=300
ENABLE_PARADOX_RESOLUTION=true
ENABLE_GODEL_EXPANSION=true
ENABLE_CTMS_REASONING=true

# Security
SECRET_KEY=change-this-secret-key
ENCRYPTION_KEY=change-this-encryption-key
ENVFILE

echo "✅ .env file created"
echo ""
echo "⚠️  IMPORTANT: Edit ~/GhostGoat/.env and add your API keys!"
echo "   Run: nano ~/GhostGoat/.env"
echo ""

