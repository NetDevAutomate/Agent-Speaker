"""Speaker engine — warm TTS model for low-latency speech synthesis."""

from __future__ import annotations

import hashlib
import logging
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from kokoro_onnx import Kokoro

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "am_michael"
DEFAULT_SPEED = 1.0

_KOKORO_DIR = Path.home() / ".cache" / "kokoro-onnx"
_KOKORO_MODEL = _KOKORO_DIR / "kokoro-v1.0.onnx"
_KOKORO_VOICES = _KOKORO_DIR / "voices-v1.0.bin"

_MODEL_BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

_EXPECTED_SHA256 = {
    "kokoro-v1.0.onnx": (  # pragma: allowlist secret
        "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"
    ),
    "voices-v1.0.bin": (  # pragma: allowlist secret
        "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"
    ),
}

_TARGET_SR = 48000


def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ensure_models() -> bool:
    """Download kokoro-onnx model files if missing. Uses atomic rename to prevent corruption."""
    if _KOKORO_MODEL.exists() and _KOKORO_VOICES.exists():
        return True
    _KOKORO_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        target = _KOKORO_DIR / name
        if not target.exists():
            tmp = _KOKORO_DIR / f".{name}.download"
            try:
                logger.info("Downloading %s...", name)
                urllib.request.urlretrieve(f"{_MODEL_BASE_URL}/{name}", str(tmp))
                digest = _sha256(tmp)
                expected = _EXPECTED_SHA256.get(name)
                if expected and digest != expected:
                    logger.warning(
                        "Checksum mismatch for %s: expected %s, got %s", name, expected, digest
                    )
                    tmp.unlink(missing_ok=True)
                    return False
                tmp.rename(target)
            except Exception:
                logger.warning("Failed to download %s", name, exc_info=True)
                tmp.unlink(missing_ok=True)
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
        except Exception:
            logger.warning("Failed to load Kokoro model", exc_info=True)
            return False

    def synthesize(
        self, text: str, *, voice: str = DEFAULT_VOICE, speed: float = DEFAULT_SPEED
    ) -> tuple[np.ndarray, int] | None:
        """Synthesize text to audio samples. Returns (samples, sample_rate) or None."""
        if not self.load():
            return None
        if self._kokoro is None:  # type narrowing — load() guarantees this
            return None
        try:
            samples, sr = self._kokoro.create(text, voice=voice, speed=speed, lang="en-us")
            if sr != _TARGET_SR:
                ratio = _TARGET_SR / sr
                if ratio == int(ratio):
                    samples = np.repeat(samples, int(ratio))
                else:
                    samples = np.interp(
                        np.linspace(0, len(samples), int(len(samples) * ratio), endpoint=False),
                        np.arange(len(samples)),
                        samples,
                    ).astype(np.float32)
                sr = _TARGET_SR
            return samples, sr
        except Exception:
            logger.warning("TTS synthesis failed", exc_info=True)
            return None

    def speak(self, text: str, *, voice: str = DEFAULT_VOICE, speed: float = DEFAULT_SPEED) -> bool:
        """Synthesize and play text. Returns True on success."""
        result = self.synthesize(text, voice=voice, speed=speed)
        if result is None:
            return False
        samples, sr = result
        try:
            import sounddevice as sd

            sd.play(samples, sr)
            return True
        except Exception:
            logger.warning("Audio playback failed", exc_info=True)
            return False
