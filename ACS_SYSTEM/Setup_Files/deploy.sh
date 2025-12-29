#!/bin/bash

# Complete Deployment Script for CRYSTALS Crypto System
# Deploys full security stack with monitoring

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║   CRYSTALS Post-Quantum Cryptography System Deploy    ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Install CRYSTALS
echo -e "${BLUE}[1/5] Installing CRYSTALS cryptography...${NC}"
bash install.sh

# Step 2: Run tests
echo -e "${BLUE}[2/5] Running cryptographic tests...${NC}"
source ~/crystal_env/bin/activate
python3 crystal_system.py --test

# Step 3: Generate keys
echo -e "${BLUE}[3/5] Generating initial keypairs...${NC}"
python3 crystal_system.py --keygen
echo "Keys stored in current directory"

# Step 4: Set up Docker stack
echo -e "${BLUE}[4/5] Deploying security monitoring stack...${NC}"
if command -v docker-compose &> /dev/null; then
    echo "Starting Docker containers..."
    docker-compose up -d
    echo "Waiting for services to start..."
    sleep 10
else
    echo -e "${YELLOW}Docker Compose not found. Skipping container deployment.${NC}"
    echo "To deploy containers later, install Docker and run: docker-compose up -d"
fi

# Step 5: Create quick access scripts
echo -e "${BLUE}[5/5] Creating convenience scripts...${NC}"

cat > encrypt.sh << 'ENCRYPT_EOF'
#!/bin/bash
if [ "$#" -ne 2 ]; then
    echo "Usage: ./encrypt.sh <file> <recipient_public_key_prefix>"
    exit 1
fi
source ~/crystal_env/bin/activate
python3 crystal_system.py --encrypt "$1" --public-key "$2" --output "$1.enc"
ENCRYPT_EOF

cat > decrypt.sh << 'DECRYPT_EOF'
#!/bin/bash
if [ "$#" -ne 2 ]; then
    echo "Usage: ./decrypt.sh <encrypted_file> <my_private_key_prefix>"
    exit 1
fi
source ~/crystal_env/bin/activate
python3 crystal_system.py --decrypt "$1" --private-key "$2"
DECRYPT_EOF

chmod +x encrypt.sh decrypt.sh

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✓ Deployment Complete!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "📋 Quick Start:"
echo "  • Encrypt: ./encrypt.sh myfile.pdf recipient_kem"
echo "  • Decrypt: ./decrypt.sh myfile.pdf.enc my_kem"
echo "  • Test: source ~/crystal_env/bin/activate && python3 crystal_system.py --test"
echo ""
echo "🔐 Your Keys:"
echo "  • KEM Keys: my_kem_public.key / my_kem_private.key"
echo "  • SIG Keys: my_sig_public.key / my_sig_private.key"
echo ""
echo "🌐 Services (if Docker is running):"
echo "  • Kibana Dashboard: http://localhost:5601"
echo "  • SonarQube: http://localhost:9000"
echo "  • Security Dashboard: http://localhost:8080"
echo ""
echo "📖 Full documentation: cat README.md"
echo ""
