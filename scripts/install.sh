#!/usr/bin/env bash
# Install speaker agent for detected AI tools
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_DIR=$(dirname "$SCRIPT_DIR")

info() { echo -e "\033[0;32m✓\033[0m $*"; }
warn() { echo -e "\033[1;33m⚠\033[0m $*"; }
err()  { echo -e "\033[0;31m✗\033[0m $*"; }

link_file() {
  local src="$1" target="$2"
  mkdir -p "$(dirname "$target")"
  if [ -L "$target" ]; then
    rm "$target"
  fi
  ln -sf "$src" "$target"
  info "Linked: $(basename "$target")"
}

# Install CLI tool
echo "=== Installing speak CLI ==="
uv tool install "${REPO_DIR}[mcp]" --force 2>&1 | tail -1

# Kiro CLI
if [ -d "$HOME/.kiro" ]; then
  echo ""
  echo "=== Installing Kiro CLI agent ==="
  link_file "$REPO_DIR/agents/kiro/speaker.json" "$HOME/.kiro/agents/speaker.json"
  link_file "$REPO_DIR/agents/kiro/speaker" "$HOME/.kiro/agents/speaker"
  mkdir -p "$HOME/.kiro/agents/mcp"
  link_file "$REPO_DIR/agents/mcp/speaker-server.py" "$HOME/.kiro/agents/mcp/speaker-server.py"
  info "Kiro: use 'kiro-cli chat --agent speaker' or add to any agent's mcpServers"
fi

# Claude Code
if [ -d "$HOME/.claude" ]; then
  echo ""
  echo "=== Installing Claude Code agent ==="
  link_file "$REPO_DIR/agents/claude/speaker.md" "$HOME/.claude/speaker.md"
  info "Claude Code: add to .claude/settings.json allowedTools or use /read speaker.md"
fi

# Gemini CLI
if [ -d "$HOME/.gemini" ]; then
  echo ""
  echo "=== Installing Gemini CLI agent ==="
  link_file "$REPO_DIR/agents/claude/speaker.md" "$HOME/.gemini/speaker.md"
  info "Gemini: @speak-start / @speak-stop in any session"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Usage in any agent session:"
echo "  @speak-start    Enable voice output"
echo "  @speak-stop     Disable voice output"
echo ""
echo "Config: ~/.config/speaker/config.yaml"
echo "  tts:"
echo "    voice: am_michael"
echo "    speed: 1.0"
echo "    backend: kokoro"
