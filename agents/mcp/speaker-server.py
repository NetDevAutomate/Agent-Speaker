#!/usr/bin/env python3
"""MCP server for speaker — exposes speak() tool to AI agents."""

import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("speaker")

_SPEAK_BIN = Path.home() / ".local" / "bin" / "speak"


@mcp.tool()
def speak(text: str) -> str:
    """Speak text aloud using TTS. When voice is enabled (@speak-start), call this with your full response text (excluding code blocks)."""
    try:
        subprocess.run([str(_SPEAK_BIN), text], check=True, timeout=120, capture_output=True)
        return f"🔊 Spoke: {text[:80]}..."
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"TTS failed: {e}"


if __name__ == "__main__":
    mcp.run()
