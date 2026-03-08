"""MCP server for speaker — exposes speak() tool with a warm TTS model.

The Kokoro model loads once at first call and stays in memory,
eliminating the ~2-4s cold-start penalty on every invocation.
"""

from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

from speaker.engine import SpeakerEngine

mcp = FastMCP("speaker")
_engine = SpeakerEngine()

_VOICE_PATTERN = re.compile(r"^[a-z]{2}_[a-z]{2,20}$")
_MAX_TEXT_LENGTH = 10_000
_MIN_SPEED = 0.5
_MAX_SPEED = 2.0
_RESPONSE_PREVIEW_LENGTH = 80


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
    if not _VOICE_PATTERN.match(voice):
        return f"Invalid voice name: {voice}. Expected format: am_michael, af_heart, etc."
    speed = max(_MIN_SPEED, min(_MAX_SPEED, speed))
    text = text[:_MAX_TEXT_LENGTH]

    if _engine.speak(text, voice=voice, speed=speed):
        preview = text[:_RESPONSE_PREVIEW_LENGTH]
        suffix = "..." if len(text) > _RESPONSE_PREVIEW_LENGTH else ""
        return f"Spoke: {preview}{suffix}"
    return "TTS failed — check that kokoro-onnx models are downloaded."


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
