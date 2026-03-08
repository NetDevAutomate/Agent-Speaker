# Speaker — Voice Output for AI Agents

You have a voice output tool via MCP. The user controls it with:

- `/speak-start` — enable voice
- `/speak-stop` — disable voice

Voice is **off by default**.

When enabled, call the `speak` MCP tool after each response with your full response text.
Exclude code blocks from spoken text. If the tool fails, continue without voice.
