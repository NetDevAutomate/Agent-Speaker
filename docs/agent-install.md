# Agent Installation Guide

## Prerequisites

Install the `speak` CLI and `speak-mcp` MCP server:
```bash
cd ~/code/personal/tools/speaker
uv tool install .[mcp] --force
```

Verify:
```bash
speak "test"          # CLI works
which speak-mcp       # MCP server installed
```

## Install Script

The easiest path — auto-detects installed AI tools:
```bash
./scripts/install.sh
```

```mermaid
flowchart TD
    A[install.sh] --> B[uv tool install speaker]
    B --> C{~/.kiro exists?}
    C -->|yes| D[Symlink Kiro agent config]
    C -->|no| E{~/.claude exists?}
    D --> E
    E -->|yes| F[Install MCP config + slash commands]
    E -->|no| G{~/.gemini exists?}
    F --> G
    G -->|yes| H[Install MCP config]
    G -->|no| I[Done]
    H --> I
```

## How All Agents Connect

Every agent uses the same MCP server (`speak-mcp`). The only difference is where each agent stores its MCP config.

```mermaid
graph LR
    subgraph "Agents"
        K[Kiro CLI]
        C[Claude Code]
        G[Gemini CLI]
        O[OpenCode]
        CR[Crush]
    end

    subgraph "MCP Server"
        S[speak-mcp]
    end

    subgraph "Engine"
        E[SpeakerEngine<br/>kokoro-onnx]
    end

    K -->|MCP stdio| S
    C -->|MCP stdio| S
    G -->|MCP stdio| S
    O -->|MCP stdio| S
    CR -->|MCP stdio| S
    S --> E
```

## Kiro CLI

The install script handles this, but here's the manual setup.

**Files needed:**
- `~/.kiro/agents/speaker.json` — agent definition with MCP server config
- `~/.kiro/agents/speaker/persona.md` — system prompt

**speaker.json:**
```json
{
  "name": "speaker",
  "description": "Voice output for AI agents — speak responses aloud using high-quality local TTS",
  "prompt": "file://speaker/persona.md",
  "resources": ["file://speaker/persona.md"],
  "tools": ["@builtin", "@speaker"],
  "mcpServers": {
    "speaker": {
      "command": "speak-mcp",
      "args": [],
      "env": {"FASTMCP_LOG_LEVEL": "ERROR"}
    }
  },
  "allowedTools": ["mcp_speaker_speak"]
}
```

**Usage:**
```bash
kiro-cli chat --agent speaker
```

**Adding to an existing agent** — merge the `mcpServers` and `allowedTools` into your agent's JSON, and add voice toggle instructions to its persona.

## Claude Code

**Files needed:**
- `~/.claude/mcp.json` — MCP server config
- `~/.claude/commands/speak-start.md` — slash command to enable voice
- `~/.claude/commands/speak-stop.md` — slash command to disable voice
- `~/.claude/speaker.md` — system prompt with voice toggle instructions

**mcp.json:**
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

**speaker.md** (loaded as context):
```markdown
You have a voice output tool via MCP. The user controls it with:
- /speak-start — enable voice
- /speak-stop — disable voice

Voice is off by default.
When enabled, call the speak MCP tool after each response with your full response text.
Exclude code blocks from spoken text.
```

**Usage:** In any Claude Code session:
```
/speak-start
```

## Gemini CLI

**File needed:**
- `~/.gemini/mcp.json` — MCP server config

**mcp.json:**
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

**Usage:** In any Gemini session:
```
@speak-start
```

## OpenCode

**File needed:**
- MCP config in your OpenCode settings (typically `~/.config/opencode/mcp.json`)

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

Add to your agent's system prompt:
```
The user can toggle voice with @speak-start and @speak-stop.
When enabled, call the speak tool with your full response text.
Exclude code blocks from spoken text.
```

## Crush

**File needed:**
- `crush.json` in your project root

```json
{
  "$schema": "https://charm.land/crush.json",
  "mcp": {
    "speaker": {
      "type": "stdio",
      "command": "speak-mcp",
      "args": [],
      "timeout": 120
    }
  }
}
```

## Amp

Amp supports MCP servers. Add to your Amp config:

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

And add to `AGENTS.md` in the project root:
```markdown
## Voice Output

The user can toggle voice with @speak-start and @speak-stop.
When enabled, call the speak tool with your full response text.
Exclude code blocks from spoken text.
```
