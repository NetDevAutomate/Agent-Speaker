"""MCP server for speaker — exposes speak() tool with a warm TTS model.

The Kokoro model loads once at first call and stays in memory,
eliminating the ~2-4s cold-start penalty on every invocation.
"""

from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

from speaker.engine import (
    _KOKORO_MODEL,
    _KOKORO_VOICES,
    DEFAULT_SPEED,
    DEFAULT_VOICE,
    SpeakerEngine,
)

mcp = FastMCP("speaker")
_engine = SpeakerEngine()

_VOICE_PATTERN = re.compile(r"^[a-z]{2}_[a-z]{2,20}$")
_MAX_TEXT_LENGTH = 2_000
_MIN_SPEED = 0.5
_MAX_SPEED = 2.0
_RESPONSE_PREVIEW_LENGTH = 80


@mcp.tool()
def speak(text: str, voice: str = DEFAULT_VOICE, speed: float = DEFAULT_SPEED) -> str:
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


@mcp.tool()
def list_voices() -> str:
    """List available TTS voice names.

    Returns the full set of kokoro-onnx voices. Voice names follow
    the pattern {accent}{gender}_{name}, e.g. am_michael, af_heart.
    """
    voices = _engine.get_voices()
    if voices is None:
        return "Could not load voices — model may not be available."
    return "\n".join(voices)


@mcp.tool()
def speaker_status() -> str:
    """Check the status of the TTS engine.

    Returns model loaded state, file paths, and available voice count.
    Useful for diagnosing TTS issues.
    """
    lines = [
        f"Model loaded: {_engine.is_loaded}",
        f"Model path: {_KOKORO_MODEL}",
        f"Models downloaded: {_KOKORO_MODEL.exists() and _KOKORO_VOICES.exists()}",
    ]
    voices = _engine.get_voices()
    if voices is not None:
        lines.append(f"Available voices: {len(voices)}")
    return "\n".join(lines)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
