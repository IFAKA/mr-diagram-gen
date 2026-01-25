#!/bin/bash
# One-command install for mr-diagram-gen

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Icons
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
ARROW="${BLUE}→${NC}"
WARN="${YELLOW}!${NC}"

echo ""
echo -e "${BOLD}mr-diagram-gen installer${NC}"
echo -e "────────────────────────"
echo ""

# Step 1: Python
echo -e "${ARROW} Checking Python..."
if command -v python3 &> /dev/null; then
    PYVER=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "  ${CHECK} Python ${PYVER}"
else
    echo -e "  ${CROSS} Python 3 not found"
    echo -e "  ${WARN} Install from https://python.org"
    exit 1
fi

# Step 2: Install package
echo ""
echo -e "${ARROW} Installing mr-diagram-gen..."
if pip install --quiet git+https://github.com/IFAKA/mr-diagram-gen.git 2>/dev/null; then
    echo -e "  ${CHECK} Package installed"
else
    echo -e "  ${CROSS} Installation failed"
    exit 1
fi

# Step 3: Ollama
echo ""
echo -e "${ARROW} Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo -e "  ${CHECK} Ollama installed"
else
    echo -e "  ${WARN} Ollama not found"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo ""
        read -p "    Install via Homebrew? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            echo -e "  ${ARROW} Installing Ollama..."
            if brew install ollama 2>/dev/null; then
                echo -e "  ${CHECK} Ollama installed"
            else
                echo -e "  ${CROSS} Failed to install Ollama"
            fi
        else
            echo -e "  ${WARN} Skipped (LLM features won't work)"
        fi
    else
        echo -e "  ${WARN} Install from: https://ollama.ai"
    fi
fi

# Step 4: Model
echo ""
echo -e "${ARROW} Checking LLM model..."
if command -v ollama &> /dev/null; then
    if ollama list 2>/dev/null | grep -q "codellama"; then
        MODEL=$(ollama list 2>/dev/null | grep "codellama" | head -1 | awk '{print $1}')
        echo -e "  ${CHECK} Model found: ${MODEL}"
    else
        echo -e "  ${WARN} No codellama model found"
        echo ""
        read -p "    Pull codellama:7b (~4GB download)? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            echo -e "  ${ARROW} Pulling model (this takes a few minutes)..."
            if ollama pull codellama:7b; then
                echo -e "  ${CHECK} Model ready"
            else
                echo -e "  ${CROSS} Failed to pull model"
            fi
        else
            echo -e "  ${WARN} Skipped (use --mock-llm flag to test without model)"
        fi
    fi
else
    echo -e "  ${WARN} Skipped (Ollama not installed)"
fi

# Step 5: Mermaid CLI
echo ""
echo -e "${ARROW} Checking diagram renderer..."
if command -v mmdc &> /dev/null; then
    echo -e "  ${CHECK} mermaid-cli installed"
else
    if command -v npm &> /dev/null; then
        echo -e "  ${WARN} mermaid-cli not found"
        echo ""
        read -p "    Install for PNG rendering? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            echo -e "  ${ARROW} Installing mermaid-cli..."
            if npm install -g @mermaid-js/mermaid-cli 2>/dev/null; then
                echo -e "  ${CHECK} mermaid-cli installed"
            else
                echo -e "  ${CROSS} Failed (try: sudo npm install -g @mermaid-js/mermaid-cli)"
            fi
        else
            echo -e "  ${WARN} Skipped (diagrams will be Mermaid code only)"
        fi
    else
        echo -e "  ${WARN} npm not found - PNG rendering unavailable"
    fi
fi

# Done
echo ""
echo -e "────────────────────────"
echo -e "${CHECK} ${BOLD}Installation complete${NC}"
echo ""
echo -e "  Run ${BOLD}mr-diagram-gen status${NC} to verify setup"
echo ""
echo -e "  Quick start:"
echo -e "    cd your-project"
echo -e "    mr-diagram-gen analyze --local"
echo ""
