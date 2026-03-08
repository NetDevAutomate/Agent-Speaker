# Speaker

> Local TTS for AI coding agents — speak responses aloud

Adds voice output to any AI coding agent (Claude Code, Kiro CLI, Gemini CLI, OpenCode, Crush, Amp). Uses [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (82M params) for fast, natural-sounding speech with ~1.5s latency.

All agents integrate via an [MCP](https://modelcontextprotocol.io/) server that exposes a `speak` tool. The Kokoro model loads once and stays warm in memory, eliminating cold-start latency on subsequent calls.

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

This installs the `speak` CLI, the `speak-mcp` MCP server, and configures any detected AI tools.

## Usage

In any agent session:

| Platform | Enable | Disable |
|----------|--------|---------|
| Claude Code | `/speak-start` | `/speak-stop` |
| Kiro CLI | `@speak-start` | `@speak-stop` |
| Gemini CLI | `@speak-start` | `@speak-stop` |
| OpenCode | `@speak-start` | `@speak-stop` |
| Amp | `@speak-start` | `@speak-stop` |

Voice is off by default. When enabled, the agent calls the `speak` MCP tool with its full response (excluding code blocks).

## CLI

The `speak` CLI is also available standalone:

```bash
speak "Hello, can you hear me?"          # Speak text
speak -                                   # Read from stdin
speak "text" -v af_heart                  # Different voice
speak "text" -s 1.2                       # Faster
speak "text" -b macos                     # macOS say fallback
```

## MCP Server

All agent integrations use the `speak-mcp` entry point, which runs a [FastMCP](https://github.com/jlowin/fastmcp) server exposing a single `speak` tool.

The server keeps the Kokoro model warm in memory — first call loads the model (~2s), subsequent calls have ~200ms overhead.

### Tool Schema

| Field | Value |
|-------|-------|
| Name | `speak` |
| Parameters | `text: str`, `voice: str = "am_michael"`, `speed: float = 1.0` |
| Returns | `str` — confirmation or error message |

### Adding to Any Agent

Any MCP-compatible agent can use speaker. Add to your agent's MCP config:

```json
{
  "mcpServers": {
    "speaker": {
      "command": "speak-mcp",
      "args": []
    }
  }
}
```

Then add to the agent's prompt:
```
The user can toggle voice with @speak-start and @speak-stop.
When enabled, call the speak tool with your full response text.
Exclude code blocks from spoken text.
```

See [docs/agent-install.md](docs/agent-install.md) for platform-specific configs.

## Configuration

`~/.config/speaker/config.yaml`:

```yaml
tts:
  voice: am_michael      # am_michael, af_heart, bf_emma, etc.
  speed: 1.0             # 0.5 = slow, 2.0 = fast
  backend: kokoro        # kokoro | macos
  macos_voice: Samantha  # fallback voice
```

See [docs/configuration.md](docs/configuration.md) for all options.

## How It Works

1. Agent calls the `speak` MCP tool with response text
2. MCP server (`speak-mcp`) synthesizes audio via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)
3. Audio resampled 24kHz->48kHz and played via sounddevice
4. Model stays warm in memory for low-latency subsequent calls
5. Falls back to macOS `say` if kokoro is unavailable

## Architecture

```
Agent (Claude/Kiro/Gemini/...)
  |
  | MCP protocol (stdio)
  v
speak-mcp (FastMCP server)
  |
  | SpeakerEngine (in-process)
  v
kokoro-onnx -> sounddevice -> audio out
```

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for installation
- macOS or Linux (kokoro-onnx runs on CPU via ONNX Runtime)

## License

MIT
