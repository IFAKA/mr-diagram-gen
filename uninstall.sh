#!/bin/bash
# Complete uninstall - zero traces

echo "Uninstalling mr-diagram-gen..."

# Remove package
pip uninstall -y mr-diagram-gen 2>/dev/null || true

# Remove config
rm -rf ~/.config/mr-diagram

# Remove any cached diagrams in current dir
rm -rf .mr-diagrams-preview .mr-diagrams 2>/dev/null || true

echo "Done. No traces left."
echo ""
echo "Note: Ollama and mermaid-cli were not removed."
echo "To remove those too:"
echo "  brew uninstall ollama"
echo "  npm uninstall -g @mermaid-js/mermaid-cli"
