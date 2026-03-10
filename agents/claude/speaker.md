# Speaker — Voice Output for AI Agents

You have a voice output tool via MCP. The user controls it with:

- `/speak-start` — enable voice
- `/speak-stop` — disable voice

Voice is **off by default**.

When enabled, call the `speak` MCP tool after each response with your full response text.
Exclude code blocks from spoken text. If the tool fails, continue without voice.

Optional parameters:
- `voice` — default `am_michael`. Options: `af_heart`, `af_bella`, `am_adam`, `bf_emma`
- `speed` — default `1.0`. Range: `0.5` (slow) to `2.0` (fast)
