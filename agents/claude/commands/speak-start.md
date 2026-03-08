Enable voice output. From now on, after every response you write, call the `speak` MCP tool with your full response text (excluding code blocks).

If the MCP tool is not available, fall back to running: ~/.local/bin/speak "your response text here"

If both fail, continue without voice. Remember this is enabled until /speak-stop is used.
