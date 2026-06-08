#!/bin/bash

# Crystal Family Cryptography - Easy Installation Script
# Installs CRYSTALS-Kyber, CRYSTALS-Dilithium with security stack

set -e

echo "=========================================="
echo "Crystal Family Crypto Stack Installer"
echo "CRYSTALS-Kyber + CRYSTALS-Dilithium"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}Do not run as root. Run as normal user.${NC}"
   exit 1
fi

echo -e "${GREEN}[1/6] Updating system packages...${NC}"
apt-get update 

echo -e "${GREEN}[2/6] Installing dependencies...${NC}"
apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    curl \
    wget

echo -e "${GREEN}[3/6] Creating Python virtual environment...${NC}"
python3 -m venv ~/crystal_env
source ~/crystal_env/bin/activate

echo -e "${GREEN}[4/6] Installing Python crypto libraries...${NC}"
pip install --upgrade pip
pip install \
    numpy \
    pycryptodome \
    cryptography \
    scipy \
    pqcrypto \
    liboqs-python

echo -e "${GREEN}[5/6] Installing liboqs (Open Quantum Safe)...${NC}"
cd /tmp
if [ ! -d "liboqs" ]; then
    git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git
fi
cd liboqs
mkdir -p build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make -j$(nproc)
 make install
 ldconfig

echo -e "${GREEN}[6/6] Setting up Crystal Crypto System...${NC}"
cd ~/
mkdir -p crystal_crypto/{keys,encrypted,tests}

echo -e "${GREEN}Installation Complete!${NC}"
echo ""
echo "To activate the environment, run:"
echo "  source ~/crystal_env/bin/activate"
echo ""
echo "To test the system, run:"
echo "  python3 crystal_system.py --test"

