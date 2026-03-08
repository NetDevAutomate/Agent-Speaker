# Speaker — Voice Output for AI Agents

You have a voice output tool. The user controls it with:

- `/speak-start` — enable voice
- `/speak-stop` — disable voice

Voice is **off by default**.

When enabled, run this after each response:
```bash
~/.local/bin/speak "Your full response text here"
```

Exclude code blocks from spoken text. If the command fails, continue without voice.
