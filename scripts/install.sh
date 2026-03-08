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

copy_json() {
  local src="$1" target="$2"
  mkdir -p "$(dirname "$target")"
  cp "$src" "$target"
  info "Installed: $(basename "$target")"
}

# Install CLI tool + MCP server entry point
echo "=== Installing speak CLI and MCP server ==="
uv tool install "${REPO_DIR}[mcp]" --force 2>&1 | tail -1

# Kiro CLI
if [ -d "$HOME/.kiro" ]; then
  echo ""
  echo "=== Installing Kiro CLI agent ==="
  link_file "$REPO_DIR/agents/kiro/speaker.json" "$HOME/.kiro/agents/speaker.json"
  link_file "$REPO_DIR/agents/kiro/speaker" "$HOME/.kiro/agents/speaker"
  info "Kiro: use 'kiro-cli chat --agent speaker' or add to any agent's mcpServers"
fi

# Claude Code
if [ -d "$HOME/.claude" ]; then
  echo ""
  echo "=== Installing Claude Code agent ==="
  mkdir -p "$HOME/.claude/commands"
  link_file "$REPO_DIR/agents/claude/commands/speak-start.md" "$HOME/.claude/commands/speak-start.md"
  link_file "$REPO_DIR/agents/claude/commands/speak-stop.md" "$HOME/.claude/commands/speak-stop.md"
  copy_json "$REPO_DIR/agents/claude/mcp.json" "$HOME/.claude/mcp.json"
  link_file "$REPO_DIR/agents/claude/speaker.md" "$HOME/.claude/speaker.md"
  info "Claude Code: use /speak-start and /speak-stop"
fi

# Gemini CLI
if [ -d "$HOME/.gemini" ]; then
  echo ""
  echo "=== Installing Gemini CLI agent ==="
  mkdir -p "$HOME/.gemini"
  copy_json "$REPO_DIR/agents/gemini/mcp.json" "$HOME/.gemini/mcp.json"
  info "Gemini: @speak-start / @speak-stop in any session"
fi

echo ""
echo "=== Done ==="
echo ""
echo "All agents use the speaker MCP server (speak-mcp entry point)."
echo "The speak tool is available as a native tool in each agent."
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
