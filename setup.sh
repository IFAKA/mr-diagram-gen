#!/bin/bash
# One-command install for mr-diagram-gen

set -e

echo "Installing mr-diagram-gen..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 required. Install from https://python.org"
    exit 1
fi

# Install the package
pip install --quiet git+https://github.com/IFAKA/mr-diagram-gen.git

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo ""
    echo "Ollama not found."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        read -p "Install Ollama via Homebrew? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            brew install ollama
        fi
    else
        echo "Install from: https://ollama.ai"
    fi
fi

# Check for model
if command -v ollama &> /dev/null; then
    if ! ollama list 2>/dev/null | grep -q "codellama"; then
        echo ""
        read -p "Pull codellama:7b model? (~4GB) [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            ollama pull codellama:7b
        fi
    fi
fi

# Check for mermaid-cli
if ! command -v mmdc &> /dev/null; then
    if command -v npm &> /dev/null; then
        echo ""
        read -p "Install mermaid-cli for diagram rendering? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            npm install -g @mermaid-js/mermaid-cli
        fi
    else
        echo "npm not found. Diagrams will be Mermaid code only (no PNG)."
    fi
fi

echo ""
echo "Done! Run 'mr-diagram-gen status' to check setup."
echo ""
echo "Quick start:"
echo "  cd your-project"
echo "  mr-diagram-gen analyze --local"
