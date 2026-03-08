"""Speaker engine — warm TTS model for low-latency speech synthesis."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from kokoro_onnx import Kokoro

_KOKORO_DIR = Path.home() / ".cache" / "kokoro-onnx"
_KOKORO_MODEL = _KOKORO_DIR / "kokoro-v1.0.onnx"
_KOKORO_VOICES = _KOKORO_DIR / "voices-v1.0.bin"

_TARGET_SR = 48000


def _ensure_models() -> bool:
    """Download kokoro-onnx model files if missing."""
    if _KOKORO_MODEL.exists() and _KOKORO_VOICES.exists():
        return True
    _KOKORO_DIR.mkdir(parents=True, exist_ok=True)
    base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        if not (_KOKORO_DIR / name).exists():
            try:
                subprocess.run(
                    ["wget", "-q", f"{base}/{name}", "-O", str(_KOKORO_DIR / name)],
                    check=True,
                    timeout=300,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False
    return _KOKORO_MODEL.exists() and _KOKORO_VOICES.exists()


class SpeakerEngine:
    """TTS engine that keeps the Kokoro model warm in memory."""

    def __init__(self) -> None:
        self._kokoro: Kokoro | None = None

    @property
    def is_loaded(self) -> bool:
        return self._kokoro is not None

    def load(self) -> bool:
        """Load the Kokoro model. Returns True on success."""
        if self._kokoro is not None:
            return True
        if not _ensure_models():
            return False
        try:
            from kokoro_onnx import Kokoro

            self._kokoro = Kokoro(str(_KOKORO_MODEL), str(_KOKORO_VOICES))
            return True
        except Exception:  # noqa: BLE001
            return False

    def synthesize(
        self, text: str, *, voice: str = "am_michael", speed: float = 1.0
    ) -> tuple[np.ndarray, int] | None:
        """Synthesize text to audio samples. Returns (samples, sample_rate) or None."""
        if not self.load():
            return None
        assert self._kokoro is not None
        try:
            samples, sr = self._kokoro.create(text, voice=voice, speed=speed, lang="en-us")
            if sr != _TARGET_SR:
                samples = np.interp(
                    np.linspace(
                        0, len(samples), int(len(samples) * _TARGET_SR / sr), endpoint=False
                    ),
                    np.arange(len(samples)),
                    samples,
                ).astype(np.float32)
                sr = _TARGET_SR
            return samples, sr
        except Exception:  # noqa: BLE001
            return None

    def speak(self, text: str, *, voice: str = "am_michael", speed: float = 1.0) -> bool:
        """Synthesize and play text. Returns True on success."""
        result = self.synthesize(text, voice=voice, speed=speed)
        if result is None:
            return False
        samples, sr = result
        try:
            import sounddevice as sd

            sd.play(samples, sr)
            sd.wait()
            return True
        except Exception:  # noqa: BLE001
            return False
