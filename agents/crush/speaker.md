# Speaker — Voice Output for AI Agents

You have a voice output tool called `speak`. The user controls it with:

- `@speak-start` — enable voice (remember this state)
- `@speak-stop` — disable voice

Voice is **off by default**.

When voice is enabled, call the `speak` tool with your full response text after each reply. Exclude code blocks — those don't work spoken aloud.

If the tool fails, continue without voice.

Optional parameters:
- `voice` — default `am_michael`. Options: `af_heart`, `af_bella`, `am_adam`, `bf_emma`
- `speed` — default `1.0`. Range: `0.5` (slow) to `2.0` (fast)
