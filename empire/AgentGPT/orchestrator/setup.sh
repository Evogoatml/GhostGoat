#!/usr/bin/env bash
# Quantum-Adaptive Crypto Orchestrator Setup Script

set -e

echo "========================================"
echo "Quantum-Adaptive Crypto Orchestrator"
echo "Setup & Installation Script"
echo "========================================"
echo ""

# Detect environment
if command -v termux-setup-storage &> /dev/null; then
    ENV="termux"
    PIP_FLAGS="--break-system-packages"
    echo "Environment: Termux/Android"
else
    ENV="standard"
    PIP_FLAGS=""
    echo "Environment: Standard Linux"
fi

# Check Python version
echo ""
echo "Checking Python version..."
python3 --version

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install pycryptodome numpy $PIP_FLAGS

echo ""
read -p "Install optional ML libraries? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install scikit-learn pandas $PIP_FLAGS
fi

# Clone repositories
echo ""
echo "========================================"
echo "Cloning Required Repositories"
echo "========================================"

cd ai_resources

echo ""
echo "[1/8] Cloning Machine Learning Algorithms..."
if [ ! -d "ml_algorithms/.git" ]; then
    git clone --depth 1 https://github.com/milaan9/Machine_Learning_Algorithms_from_Scratch.git ml_algorithms/
else
    echo "  Already exists, skipping..."
fi

echo ""
echo "[2/8] Cloning NLP Resources..."
if [ ! -d "nlp/.git" ]; then
    git clone --depth 1 https://github.com/milaan9/Python_Natural_Language_Processing.git nlp/
else
    echo "  Already exists, skipping..."
fi

echo ""
echo "[3/8] Cloning Algorithm Implementations..."
if [ ! -d "algorithms/.git" ]; then
    git clone --depth 1 https://github.com/subbarayudu-j/TheAlgorithms-Python.git algorithms/
else
    echo "  Already exists, skipping..."
fi

echo ""
echo "[4/8] Cloning ML Models..."
if [ ! -d "ml_models/.git" ]; then
    git clone --depth 1 https://github.com/subbarayudu-j/MachineLearning-sklearn-pandas.git ml_models/
else
    echo "  Already exists, skipping..."
fi

echo ""
echo "[5/8] Cloning RAG Resources..."
if [ ! -d "rag/.git" ]; then
    git clone --depth 1 https://github.com/emrgnt-cmplxty/RAGHub.git rag/
else
    echo "  Already exists, skipping..."
fi

cd ../agent_frameworks

echo ""
echo "[6/8] Cloning SuperAGI..."
if [ ! -d "superagi/.git" ]; then
    git clone --depth 1 https://github.com/TransformerOptimus/SuperAGI.git superagi/
else
    echo "  Already exists, skipping..."
fi

echo ""
echo "[7/8] Cloning Scripts..."
if [ ! -d "scripts/.git" ]; then
    git clone --depth 1 https://github.com/Esther7171/Scripts.git scripts/
    git clone --depth 1 https://github.com/sangampaudel530/Mini_Python_Projects.git scripts/mini_projects/
else
    echo "  Already exists, skipping..."
fi

cd ../security_research

echo ""
echo "[8/8] Cloning Security Research..."
read -p "Clone RAT collection? (for defensive research only) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d "analysis/.git" ]; then
        git clone --depth 1 https://github.com/Cryakl/Ultimate-RAT-Collection.git analysis/
    else
        echo "  Already exists, skipping..."
    fi
else
    echo "  Skipped (recommended for security)"
fi

cd ..

# Run tests
echo ""
echo "========================================"
echo "Running System Tests"
echo "========================================"
echo ""

python3 test_audit.py

# Generate initial report
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Review test results above"
echo "  2. Run demo: python3 main.py"
echo "  3. Check audit report: /tmp/qac_test_report.json"
echo ""
echo "Integration with your systems:"
echo "  - GhostGoatNode: Import from core/crypto_engine"
echo "  - META GOAT V2: Use core/ai_orchestrator"
echo "  - ADAP: Integrate core/network_security"
echo ""
echo "For network defense (requires root):"
echo "  sudo python3 main.py --enable-network-defense"
echo ""
