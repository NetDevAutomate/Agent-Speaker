"""MCP server for speaker — exposes speak() tool with a warm TTS model.

The Kokoro model loads once at first call and stays in memory,
eliminating the ~2-4s cold-start penalty on every invocation.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from speaker.engine import SpeakerEngine

mcp = FastMCP("speaker")
_engine = SpeakerEngine()


@mcp.tool()
def speak(text: str, voice: str = "am_michael", speed: float = 1.0) -> str:
    """Speak text aloud using high-quality local TTS.

    Call this with the full response text (excluding code blocks)
    when the user has enabled voice output.

    Args:
        text: The text to speak aloud.
        voice: Voice name (am_michael, af_heart, bf_emma, etc.).
        speed: Speech speed from 0.5 (slow) to 2.0 (fast).
    """
    if not text.strip():
        return "No text provided."
    if _engine.speak(text, voice=voice, speed=speed):
        return f"Spoke: {text[:80]}..."
    return "TTS failed — check that kokoro-onnx models are downloaded."


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
