# Architecture & Code Map

Speaker is a local TTS tool with two layers: an engine that wraps kokoro-onnx, and an MCP server that exposes it as a tool. Agent configs teach AI assistants how to use it.

## Component Diagram

```mermaid
graph TB
    subgraph "Agent Layer"
        KA[Kiro CLI Agent<br/>speaker.json + persona.md]
        CA[Claude Code Agent<br/>mcp.json + speaker.md]
        GA[Gemini CLI<br/>mcp.json]
        OA[OpenCode / Crush / Amp<br/>mcp.json or config]
    end

    subgraph "MCP Server"
        MCP[speak-mcp<br/>FastMCP server<br/>src/speaker/mcp_server.py]
    end

    subgraph "Engine"
        ENG[SpeakerEngine<br/>src/speaker/engine.py]
    end

    subgraph "Backend"
        KO[kokoro-onnx<br/>82M ONNX TTS model]
        SD[sounddevice<br/>audio playback]
    end

    subgraph "Storage"
        MODEL[~/.cache/kokoro-onnx/<br/>model + voices]
    end

    KA -->|MCP protocol| MCP
    CA -->|MCP protocol| MCP
    GA -->|MCP protocol| MCP
    OA -->|MCP protocol| MCP
    MCP --> ENG
    ENG --> KO
    ENG --> SD
    KO -.->|loads| MODEL
```

## Data Flow

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as speak-mcp server
    participant Engine as SpeakerEngine
    participant Kokoro as kokoro-onnx
    participant Audio as sounddevice

    Agent->>MCP: MCP call: speak(text="Hello world")
    MCP->>MCP: Validate voice, clamp speed, cap text length
    MCP->>Engine: engine.speak("Hello world")
    Note over Engine: Model loaded on first call,<br/>stays warm in memory
    Engine->>Kokoro: create(text, voice, speed)
    Kokoro->>Kokoro: Generate samples (24kHz)
    Kokoro-->>Engine: samples, sample_rate
    Engine->>Engine: Resample 24kHz -> 48kHz
    Engine->>Audio: sd.play(samples, 48000)
    Note over Audio: Non-blocking — audio plays<br/>in background thread
    Engine-->>MCP: True
    MCP-->>Agent: "Spoke: Hello world..."
```

## Module Breakdown

### `src/speaker/engine.py` — TTS Engine

The core module. A `SpeakerEngine` class that:

- Downloads kokoro-onnx model files on first use (~337MB to `~/.cache/kokoro-onnx/`) via urllib with atomic rename and SHA-256 verification
- Loads the model once and keeps it warm in memory
- Synthesizes text to audio, resamples 24kHz->48kHz
- Plays audio via sounddevice

Key components:

| Component | Purpose |
|-----------|---------|
| `DEFAULT_VOICE`, `DEFAULT_SPEED` | Shared constants for defaults |
| `_EXPECTED_SHA256` | Hardcoded SHA-256 hashes for model integrity verification |
| `_sha256()` | Compute SHA-256 digest of a downloaded file |
| `_ensure_models()` | Download ONNX model + voices via urllib, atomic temp-file rename, SHA-256 check |
| `SpeakerEngine.load()` | Lazy-load Kokoro model into memory |
| `SpeakerEngine.synthesize()` | Generate audio samples from text |
| `SpeakerEngine.speak()` | Synthesize + play audio |

### `src/speaker/mcp_server.py` — MCP Server

A FastMCP server exposing one tool:

- `speak(text, voice, speed)` — validates inputs, calls `SpeakerEngine.speak()` directly (in-process)
- Input validation: voice regex, speed clamped 0.5-2.0, text capped at 10k chars
- Returns confirmation string or error message
- Entry point: `speak-mcp` (installed via `uv tool install`)

All agent integrations use this server via MCP protocol over stdio.

### Agent Configs

| File | Purpose |
|------|---------|
| `agents/kiro/speaker.json` | Kiro agent definition with MCP server config |
| `agents/kiro/speaker/persona.md` | Kiro system prompt with voice toggle |
| `agents/claude/mcp.json` | Claude Code MCP server config |
| `agents/claude/speaker.md` | Claude Code system prompt with voice toggle |
| `agents/claude/commands/speak-start.md` | Claude Code slash command to enable voice |
| `agents/claude/commands/speak-stop.md` | Claude Code slash command to disable voice |
| `agents/gemini/mcp.json` | Gemini CLI MCP server config |
| `agents/gemini/speaker.md` | Gemini CLI system prompt with voice toggle |
| `agents/opencode/mcp.json` | OpenCode MCP server config |
| `agents/opencode/speaker.md` | OpenCode system prompt with voice toggle |
| `agents/crush/crush.json` | Crush MCP server config |
| `agents/crush/speaker.md` | Crush system prompt with voice toggle |
| `agents/amp/mcp.json` | Amp MCP server config |
| `agents/amp/speaker.md` | Amp system prompt with voice toggle |

### `scripts/install.sh` — Installer

- Installs `speak-mcp` server via `uv tool install`
- Detects Kiro CLI, Claude Code, Gemini CLI, OpenCode
- Merges MCP config and installs system prompts (non-destructive)
- Crush and Amp use project-level configs — shipped in `agents/` but not auto-installed

## Dependencies

| Package | Role |
|---------|------|
| `kokoro-onnx` | ONNX TTS model wrapper |
| `sounddevice` | Cross-platform audio playback |
| `numpy` | Audio resampling (`np.repeat` for integer ratios, `np.interp` fallback) |
| `mcp[cli]` | MCP server framework |
