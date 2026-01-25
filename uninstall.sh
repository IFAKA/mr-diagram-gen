#!/bin/bash
# Complete uninstall - zero traces

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

CHECK="${GREEN}✓${NC}"
ARROW="${BLUE}→${NC}"
WARN="${YELLOW}!${NC}"

echo ""
echo -e "${BOLD}mr-diagram-gen uninstaller${NC}"
echo -e "──────────────────────────"
echo ""

# Remove package
echo -e "${ARROW} Removing package..."
if pip uninstall -y mr-diagram-gen 2>/dev/null; then
    echo -e "  ${CHECK} Package removed"
else
    echo -e "  ${CHECK} Package not installed (already clean)"
fi

# Remove config
echo ""
echo -e "${ARROW} Removing config..."
if [ -d ~/.config/mr-diagram ]; then
    rm -rf ~/.config/mr-diagram
    echo -e "  ${CHECK} Config removed"
else
    echo -e "  ${CHECK} No config found (already clean)"
fi

# Remove local diagrams
echo ""
echo -e "${ARROW} Cleaning up diagram cache..."
rm -rf .mr-diagrams-preview .mr-diagrams 2>/dev/null
echo -e "  ${CHECK} Local diagrams cleaned"

# Done
echo ""
echo -e "──────────────────────────"
echo -e "${CHECK} ${BOLD}Uninstall complete${NC}"
echo ""
echo -e "  Zero traces left."
echo ""
echo -e "  ${WARN} Ollama and mermaid-cli were kept (shared tools)"
echo -e "    To remove those too:"
echo -e "      brew uninstall ollama"
echo -e "      npm uninstall -g @mermaid-js/mermaid-cli"
echo ""
