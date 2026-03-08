# Architecture & Code Map

Speaker is a local TTS tool with three layers: a CLI that wraps kokoro-onnx, an MCP server that exposes the CLI as a tool, and agent configs that teach AI assistants how to use it.

## Component Diagram

```mermaid
graph TB
    subgraph "Agent Layer"
        KA[Kiro CLI Agent<br/>speaker.json + persona.md]
        CA[Claude Code Agent<br/>speaker.md]
        GA[Gemini / Others<br/>shell command]
    end

    subgraph "Bridge Layer"
        MCP[speaker-server.py<br/>FastMCP server]
    end

    subgraph "CLI Layer"
        CLI[cli.py<br/>typer app]
    end

    subgraph "Engine Layer"
        KO[kokoro-onnx<br/>82M ONNX TTS model]
        SD[sounddevice<br/>audio playback]
        SAY[macOS say<br/>fallback]
    end

    subgraph "Storage"
        MODEL[~/.cache/kokoro-onnx/<br/>model + voices]
        CFG[~/.config/speaker/<br/>config.yaml]
    end

    KA -->|MCP protocol| MCP
    CA -->|shell exec| CLI
    GA -->|shell exec| CLI
    MCP -->|subprocess| CLI
    CLI --> KO
    CLI --> SAY
    KO --> SD
    CLI -.->|reads| CFG
    KO -.->|loads| MODEL
```

## Data Flow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as speaker-server.py
    participant CLI as speak CLI
    participant Kokoro as kokoro-onnx
    participant Audio as sounddevice

    Agent->>MCP: speak(text="Hello world")
    MCP->>CLI: subprocess: speak "Hello world"
    CLI->>CLI: Load ~/.config/speaker/config.yaml
    CLI->>Kokoro: create(text, voice, speed)
    Kokoro->>Kokoro: Generate samples (24kHz)
    Kokoro-->>CLI: samples, sample_rate
    CLI->>CLI: Resample 24kHz → 48kHz
    CLI->>Audio: sd.play(samples, 48000)
    Audio-->>CLI: sd.wait()
    CLI-->>MCP: exit 0
    MCP-->>Agent: "🔊 Spoke: Hello world..."
```

## Fallback Chain

```mermaid
flowchart LR
    A[speak called] --> B{backend=macos?}
    B -->|yes| C[macOS say]
    B -->|no| D{kokoro succeeds?}
    D -->|yes| E[✓ Audio plays]
    D -->|no| F[macOS say fallback]
    C --> G[✓ Audio plays]
    F --> G
```

## Module Breakdown

### `src/speaker/cli.py` — TTS Engine + CLI

The core module. A typer app with one command (`speak`) that:

- Reads text from argument or stdin (`speak -`)
- Loads config from `~/.config/speaker/config.yaml`
- Merges CLI flags over config file over defaults
- Generates audio via kokoro-onnx, resamples to 48kHz, plays via sounddevice
- Falls back to macOS `say` if kokoro fails or is unavailable

Key functions:

| Function | Purpose |
|----------|---------|
| `_load_config()` | Parse YAML config, return `tts` section |
| `_ensure_models()` | Download ONNX model + voices on first run via wget |
| `_speak_kokoro()` | Generate + play audio via kokoro-onnx + sounddevice |
| `_speak_macos()` | Fallback: shell out to macOS `say` |
| `speak()` | CLI entrypoint — resolve config, route to backend |

### `agents/mcp/speaker-server.py` — MCP Bridge

A FastMCP server exposing one tool:

- `speak(text: str) → str` — calls `~/.local/bin/speak` via subprocess
- Returns confirmation string or error message
- Timeout: 120s

Kiro CLI launches this server via the `mcpServers` config in the agent JSON. It communicates over stdio using the MCP protocol.

### `agents/kiro/speaker.json` — Kiro Agent Config

Defines the speaker agent for `kiro-cli chat --agent speaker`:

- Points to `persona.md` for the system prompt
- Declares the `speaker` MCP server (uvx + mcp run)
- Whitelists `mcp_speaker_speak` in `allowedTools`

### `agents/kiro/speaker/persona.md` — Kiro Persona

System prompt teaching the agent about `@speak-start` / `@speak-stop` toggle and how to call the speak tool.

### `agents/claude/speaker.md` — Claude Code Prompt

System prompt for Claude Code. Uses `/speak-start` / `/speak-stop` and calls the CLI directly via shell (`~/.local/bin/speak "text"`).

### `scripts/install.sh` — Installer

- Installs the `speak` CLI via `uv tool install`
- Detects Kiro CLI, Claude Code, Gemini CLI by checking for `~/.kiro`, `~/.claude`, `~/.gemini`
- Symlinks agent configs into the right locations

## Config Loading Priority

```mermaid
flowchart LR
    A[CLI flags<br/>-v -s -b] -->|override| B[config.yaml<br/>~/.config/speaker/] -->|override| C[Defaults<br/>am_michael / 1.0 / kokoro]
```

Resolved in `speak()`: CLI flag → config file → hardcoded default.

## Dependencies

| Package | Role |
|---------|------|
| `typer` | CLI framework |
| `kokoro-onnx` | ONNX TTS model wrapper |
| `sounddevice` | Cross-platform audio playback |
| `numpy` | Audio resampling (linear interpolation) |
| `pyyaml` | Config file parsing |
| `mcp[cli]` | MCP server framework (optional, for MCP bridge) |
