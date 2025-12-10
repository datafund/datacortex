#!/bin/bash
# Datacortex Installation Script
# Installs Python package, slash command, and module registration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_COMMANDS_DIR="$HOME/.claude/commands"
MODULES_DIR="$HOME/Data/.datacore/modules"

echo "=== Datacortex Installer ==="
echo ""

# Step 1: Install Python package
echo "1. Installing Python package..."
cd "$SCRIPT_DIR"
pip install -e . --quiet
echo "   ✓ Python package installed"

# Verify installation
if command -v datacortex &> /dev/null; then
    echo "   ✓ 'datacortex' command available"
else
    echo "   ⚠ 'datacortex' command not in PATH - you may need to restart your shell"
fi

# Step 2: Install slash command
echo ""
echo "2. Installing /datacortex slash command..."
mkdir -p "$CLAUDE_COMMANDS_DIR"
if [ -L "$CLAUDE_COMMANDS_DIR/datacortex.md" ]; then
    echo "   ✓ Slash command already linked"
elif [ -f "$CLAUDE_COMMANDS_DIR/datacortex.md" ]; then
    echo "   ⚠ datacortex.md exists but is not a symlink"
else
    ln -s "$SCRIPT_DIR/commands/datacortex.md" "$CLAUDE_COMMANDS_DIR/datacortex.md"
    echo "   ✓ Slash command linked to ~/.claude/commands/"
fi

# Step 3: Register as module (optional)
echo ""
echo "3. Registering as Datacore module..."
mkdir -p "$MODULES_DIR"
if [ -L "$MODULES_DIR/datacortex" ]; then
    echo "   ✓ Module already registered"
elif [ -d "$MODULES_DIR/datacortex" ]; then
    echo "   ⚠ datacortex exists but is not a symlink"
else
    ln -s "$SCRIPT_DIR" "$MODULES_DIR/datacortex"
    echo "   ✓ Module registered in ~/.datacore/modules/"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Usage:"
echo "  datacortex serve    # Start web UI at http://localhost:8765"
echo "  datacortex stats    # Show graph statistics"
echo "  /datacortex serve   # Via Claude Code slash command"
echo ""
