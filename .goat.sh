#!/bin/bash

clear
echo "════════════════════════════════════════════════════════════"
echo "🐐 GHOSTGOAT CONTROL PANEL"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "What do you want to do?"
echo ""
echo "  1) Run Claude demo (test AI)"
echo "  2) Start trading bot builder"
echo "  3) Generate code with AI"
echo "  4) Run system tests"
echo "  5) View system status"
echo "  6) Interactive Python shell"
echo "  0) Exit"
echo ""
read -p "Choose: " choice

case $choice in
    1)
        clear
        python demo_claude_ghostgoat.py
        ;;
    2)
        echo ""
        echo "🤖 AI Trading Bot Builder"
        echo ""
        python << 'PYTHON'
import os
env = {}
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            env[k] = v
            os.environ[k] = v

from anthropic import Anthropic
client = Anthropic(api_key=env['ANTHROPIC_API_KEY'])

print("Tell me what trading bot you want to build:")
task = input("> ")

print("\n🤖 Claude is planning your bot...\n")

response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1000,
    messages=[{
        "role": "user",
        "content": f"Create a detailed plan for this trading bot: {task}\n\nProvide: 1) Architecture, 2) Key functions needed, 3) Risk management, 4) Implementation steps"
    }]
)

print(response.content[0].text)
print()
PYTHON
        ;;
    3)
        echo ""
        echo "💻 AI Code Generator"
        echo ""
        python << 'PYTHON'
import os
env = {}
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            env[k] = v
            os.environ[k] = v

from anthropic import Anthropic
client = Anthropic(api_key=env['ANTHROPIC_API_KEY'])

print("What code do you want me to generate?")
task = input("> ")

print("\n🤖 Generating code...\n")

response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=2000,
    messages=[{
        "role": "user",
        "content": f"Write Python code for: {task}\n\nInclude comments and docstrings."
    }]
)

print(response.content[0].text)
print()
PYTHON
        ;;
    4)
        clear
        cd tests
        python smoke_test.py
        ;;
    5)
        clear
        echo "🐐 GhostGoat System Status"
        echo "════════════════════════════════════════════════════════════"
        echo ""
        echo "✅ Claude AI: Connected (claude-3-haiku-20240307)"
        echo "✅ Python: $(python --version)"
        echo "✅ Location: $PWD"
        echo "✅ Virtual env: Active"
        echo ""
        echo "📊 Available modules:"
        ls -1 core/ frameworks/ security/ tools/ | head -10
        echo ""
        ;;
    6)
        clear
        cd ~/GhostGoat
        source venv/bin/activate
        python -i << 'PYTHON'
import os
import sys
sys.path.insert(0, os.getcwd())

env = {}
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            env[k] = v
            os.environ[k] = v

from anthropic import Anthropic
client = Anthropic(api_key=env['ANTHROPIC_API_KEY'])

print("🐐 GhostGoat Interactive Shell")
print("Variables available: client (Claude AI)")
print()
PYTHON
        ;;
    0)
        echo "🐐 Goodbye!"
        exit 0
        ;;
esac

read -p "Press Enter to continue..."
exec bash goat.sh

