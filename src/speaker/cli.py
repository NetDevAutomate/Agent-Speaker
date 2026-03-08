#!/usr/bin/env python3
"""Speaker CLI — high-quality local TTS via kokoro-onnx.

Usage:
    speak "Hello, can you hear me?"
    speak "text" -v af_heart -s 1.2
    echo "text" | speak -
"""

from __future__ import annotations

import subprocess
import sys
from typing import Annotated

import typer
import yaml

from speaker.engine import SpeakerEngine

app = typer.Typer(add_completion=False)

_CONFIG_PATH = __import__("pathlib").Path.home() / ".config" / "speaker" / "config.yaml"


def _load_config() -> dict:
    try:
        return yaml.safe_load(_CONFIG_PATH.read_text()).get("tts", {})
    except Exception:  # noqa: BLE001
        return {}


def _speak_macos(text: str, *, voice: str) -> bool:
    try:
        subprocess.run(["say", "-v", voice, text], check=True, timeout=60)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


@app.command()
def speak(
    text: Annotated[str | None, typer.Argument(help="Text to speak (or - for stdin)")] = None,
    voice: Annotated[str | None, typer.Option("-v", "--voice", help="Voice name")] = None,
    speed: Annotated[float | None, typer.Option("-s", "--speed", help="Speed (0.5-2.0)")] = None,
    backend: Annotated[
        str | None, typer.Option("-b", "--backend", help="Backend: kokoro, macos")
    ] = None,
) -> None:
    """Speak text aloud using high-quality local TTS."""
    if text is None or text == "-":
        if sys.stdin.isatty():
            typer.echo("Usage: speak 'text' or echo 'text' | speak -", err=True)
            raise typer.Exit(1)
        text = sys.stdin.read().strip()
    if not text:
        return

    cfg = _load_config()
    voice = voice or cfg.get("voice", "am_michael")
    speed = speed or cfg.get("speed", 1.0)
    backend = backend or cfg.get("backend", "kokoro")
    macos_voice = cfg.get("macos_voice", "Samantha")

    if backend == "macos":
        _speak_macos(text, voice=macos_voice)
    else:
        engine = SpeakerEngine()
        if not engine.speak(text, voice=voice, speed=speed):
            _speak_macos(text, voice=macos_voice)


def main():
    app()


if __name__ == "__main__":
    main()
