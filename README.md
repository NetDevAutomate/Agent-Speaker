# Speaker

> 🔊 High-quality local TTS for AI coding agents — speak responses aloud

Adds voice output to any AI coding agent (Kiro CLI, Claude Code, Gemini CLI, OpenCode, Amp, Crush). Uses [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (82M params) for fast, natural-sounding speech with ~1.5s latency.

## Why?

- Auditory channel helps with focus and processing (especially for neurodivergent users)
- Hearing responses spoken reduces "wall of text" overwhelm
- Natural voice quality — not robotic, won't put you off

## Quick Start

```bash
git clone <your-repo>/speaker.git
cd speaker
./scripts/install.sh
```

This installs the `speak` CLI and configures any detected AI tools.

## Usage

In any agent session:

| Platform | Enable | Disable |
|----------|--------|---------|
| Kiro CLI | `@speak-start` | `@speak-stop` |
| Claude Code | `/speak-start` | `/speak-stop` |
| Gemini CLI | `@speak-start` | `@speak-stop` |
| OpenCode | `@speak-start` | `@speak-stop` |
| Amp | `@speak-start` | `@speak-stop` |

Voice is off by default. When enabled, the agent speaks its full response (excluding code blocks).

## CLI

```bash
speak "Hello, can you hear me?"          # Speak text
speak -                                   # Read from stdin
speak "text" -v af_heart                  # Different voice
speak "text" -s 1.2                       # Faster
speak "text" -b macos                     # macOS say fallback
```

## Configuration

`~/.config/speaker/config.yaml`:

```yaml
tts:
  voice: am_michael      # am_michael, af_heart, bf_emma, etc.
  speed: 1.0             # 0.5 = slow, 2.0 = fast
  backend: kokoro        # kokoro | macos
  macos_voice: Samantha  # fallback voice
```

## Adding to Any Existing Agent

### Kiro CLI

Add to your agent's JSON config:

```json
{
  "tools": ["@builtin", "@speaker"],
  "mcpServers": {
    "speaker": {
      "command": "uvx",
      "args": ["--from", "mcp[cli]", "mcp", "run", "~/.kiro/agents/mcp/speaker-server.py"],
      "env": {"FASTMCP_LOG_LEVEL": "ERROR"}
    }
  }
}
```

And add to the agent's persona/prompt:

```
The user can toggle voice with @speak-start and @speak-stop.
When enabled, call the speak tool with your full response text.
```

### Claude Code / Gemini / Others

Add to the agent's system prompt:

```
The user can toggle voice with @speak-start and @speak-stop (or /speak-start /speak-stop).
When enabled, run: ~/.local/bin/speak "your response text"
Exclude code blocks from spoken text.
```

## How It Works

1. `speak` CLI wraps [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) — an 82M parameter ONNX TTS model
2. Models auto-download on first run (~337MB to `~/.cache/kokoro-onnx/`)
3. Audio resampled 24kHz→48kHz to prevent crackling on some devices
4. MCP server exposes `speak()` as a native tool for Kiro CLI
5. Other agents call the CLI directly via shell

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for installation
- macOS or Linux (kokoro-onnx runs on CPU via ONNX Runtime)

## License

MIT
