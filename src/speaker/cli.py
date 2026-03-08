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
from pathlib import Path
from typing import Annotated

import typer
import yaml

app = typer.Typer(add_completion=False)

_KOKORO_DIR = Path.home() / ".cache" / "kokoro-onnx"
_KOKORO_MODEL = _KOKORO_DIR / "kokoro-v1.0.onnx"
_KOKORO_VOICES = _KOKORO_DIR / "voices-v1.0.bin"
_CONFIG_PATH = Path.home() / ".config" / "speaker" / "config.yaml"


def _load_config() -> dict:
    try:
        return yaml.safe_load(_CONFIG_PATH.read_text()).get("tts", {})
    except Exception:  # noqa: BLE001
        return {}


def _ensure_models() -> bool:
    if _KOKORO_MODEL.exists() and _KOKORO_VOICES.exists():
        return True
    _KOKORO_DIR.mkdir(parents=True, exist_ok=True)
    base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        if not (_KOKORO_DIR / name).exists():
            typer.echo(f"Downloading {name}...", err=True)
            try:
                subprocess.run(
                    ["wget", "-q", f"{base}/{name}", "-O", str(_KOKORO_DIR / name)],
                    check=True,
                    timeout=300,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False
    return _KOKORO_MODEL.exists() and _KOKORO_VOICES.exists()


def _speak_kokoro(text: str, *, voice: str, speed: float) -> bool:
    try:
        import sounddevice as sd
        from kokoro_onnx import Kokoro
        import numpy as np
    except ImportError:
        return False
    if not _ensure_models():
        return False
    try:
        kokoro = Kokoro(str(_KOKORO_MODEL), str(_KOKORO_VOICES))
        samples, sr = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
        target_sr = 48000
        if sr != target_sr:
            samples = np.interp(
                np.linspace(0, len(samples), int(len(samples) * target_sr / sr), endpoint=False),
                np.arange(len(samples)),
                samples,
            ).astype(np.float32)
            sr = target_sr
        sd.play(samples, sr)
        sd.wait()
        return True
    except Exception:  # noqa: BLE001
        return False


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
    elif _speak_kokoro(text, voice=voice, speed=speed):
        pass
    else:
        _speak_macos(text, voice=macos_voice)


def main():
    app()


if __name__ == "__main__":
    main()
