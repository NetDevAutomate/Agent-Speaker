"""Unit tests for SpeakerEngine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from speaker.engine import SpeakerEngine, _ensure_models


class TestEnsureModels:
    def test_already_exist(self, monkeypatch):
        monkeypatch.setattr("speaker.engine._KOKORO_MODEL", MagicMock(exists=lambda: True))
        monkeypatch.setattr("speaker.engine._KOKORO_VOICES", MagicMock(exists=lambda: True))
        assert _ensure_models() is True

    def test_downloads_with_atomic_rename(self, tmp_path, monkeypatch):
        model = tmp_path / "kokoro-v1.0.onnx"
        voices = tmp_path / "voices-v1.0.bin"
        monkeypatch.setattr("speaker.engine._KOKORO_DIR", tmp_path)
        monkeypatch.setattr("speaker.engine._KOKORO_MODEL", model)
        monkeypatch.setattr("speaker.engine._KOKORO_VOICES", voices)

        def fake_urlretrieve(url, filename):
            Path(filename).touch()

        monkeypatch.setattr("speaker.engine.urllib.request.urlretrieve", fake_urlretrieve)
        monkeypatch.setattr("speaker.engine._sha256", lambda _path: "fakehash")
        monkeypatch.setattr(
            "speaker.engine._EXPECTED_SHA256",
            {
                "kokoro-v1.0.onnx": "fakehash",
                "voices-v1.0.bin": "fakehash",
            },
        )
        assert _ensure_models() is True
        assert model.exists()
        assert voices.exists()
        # Temp files should not exist after successful download
        assert not (tmp_path / ".kokoro-v1.0.onnx.download").exists()
        assert not (tmp_path / ".voices-v1.0.bin.download").exists()

    def test_checksum_mismatch_rejects_download(self, tmp_path, monkeypatch):
        monkeypatch.setattr("speaker.engine._KOKORO_DIR", tmp_path)
        monkeypatch.setattr("speaker.engine._KOKORO_MODEL", tmp_path / "kokoro-v1.0.onnx")
        monkeypatch.setattr("speaker.engine._KOKORO_VOICES", tmp_path / "voices-v1.0.bin")

        def fake_urlretrieve(url, filename):
            Path(filename).touch()

        monkeypatch.setattr("speaker.engine.urllib.request.urlretrieve", fake_urlretrieve)
        monkeypatch.setattr(
            "speaker.engine._EXPECTED_SHA256",
            {
                "kokoro-v1.0.onnx": "expected_but_wrong",
                "voices-v1.0.bin": "expected_but_wrong",
            },
        )
        assert _ensure_models() is False
        # Temp file should be cleaned up on checksum mismatch
        assert not (tmp_path / ".kokoro-v1.0.onnx.download").exists()

    def test_download_failure_cleans_temp(self, tmp_path, monkeypatch):
        monkeypatch.setattr("speaker.engine._KOKORO_DIR", tmp_path)
        monkeypatch.setattr("speaker.engine._KOKORO_MODEL", tmp_path / "kokoro-v1.0.onnx")
        monkeypatch.setattr("speaker.engine._KOKORO_VOICES", tmp_path / "voices-v1.0.bin")

        def fail_urlretrieve(url, filename):
            # Simulate partial download — write temp file then fail
            Path(filename).touch()
            raise OSError("network error")

        monkeypatch.setattr("speaker.engine.urllib.request.urlretrieve", fail_urlretrieve)
        assert _ensure_models() is False
        # Temp file should be cleaned up on failure
        assert not (tmp_path / ".kokoro-v1.0.onnx.download").exists()

    def test_download_failure_no_temp(self, tmp_path, monkeypatch):
        monkeypatch.setattr("speaker.engine._KOKORO_DIR", tmp_path)
        monkeypatch.setattr("speaker.engine._KOKORO_MODEL", tmp_path / "kokoro-v1.0.onnx")
        monkeypatch.setattr("speaker.engine._KOKORO_VOICES", tmp_path / "voices-v1.0.bin")

        def fail_urlretrieve(url, filename):
            raise OSError("network error")

        monkeypatch.setattr("speaker.engine.urllib.request.urlretrieve", fail_urlretrieve)
        assert _ensure_models() is False


class TestSpeakerEngine:
    def test_lazy_load(self):
        engine = SpeakerEngine()
        assert not engine.is_loaded

    def test_load_success(self, mock_kokoro, mock_sounddevice):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            assert engine.load()
            assert engine.is_loaded

    def test_load_failure_no_models(self):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=False):
            assert not engine.load()
            assert not engine.is_loaded

    def test_load_idempotent(self, mock_kokoro, mock_sounddevice):
        """Loading twice should not re-create the model."""
        import sys

        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            engine.load()
            engine.load()
            sys.modules["kokoro_onnx"].Kokoro.assert_called_once()

    def test_synthesize_returns_samples(self, mock_kokoro, mock_sounddevice):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            result = engine.synthesize("hello")
            assert result is not None
            samples, sr = result
            assert sr == 48000
            assert isinstance(samples, np.ndarray)

    def test_synthesize_resamples_24k_to_48k(self, monkeypatch, mock_kokoro, mock_sounddevice):
        """Verify 24kHz->48kHz resampling: output should have ~2x samples."""
        monkeypatch.setattr("speaker.engine._ensure_models", lambda: True)

        fake_samples = np.zeros(2400, dtype=np.float32)
        mock_kokoro.create.return_value = (fake_samples, 24000)

        engine = SpeakerEngine()
        result = engine.synthesize("test")
        assert result is not None
        samples, sr = result
        assert sr == 48000
        assert len(samples) == pytest.approx(4800, abs=1)

    def test_synthesize_no_resample_at_48k(self, monkeypatch, mock_kokoro, mock_sounddevice):
        """If kokoro already outputs 48kHz, no resampling needed."""
        monkeypatch.setattr("speaker.engine._ensure_models", lambda: True)

        fake_samples = np.zeros(4800, dtype=np.float32)
        mock_kokoro.create.return_value = (fake_samples, 48000)

        engine = SpeakerEngine()
        result = engine.synthesize("test")
        assert result is not None
        samples, sr = result
        assert sr == 48000
        assert len(samples) == 4800

    def test_synthesize_failure(self, monkeypatch, mock_kokoro, mock_sounddevice):
        """Synthesize returns None if kokoro raises."""
        monkeypatch.setattr("speaker.engine._ensure_models", lambda: True)
        mock_kokoro.create.side_effect = RuntimeError("model error")

        engine = SpeakerEngine()
        result = engine.synthesize("test")
        assert result is None

    def test_speak_plays_audio(self, mock_kokoro, mock_sounddevice):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            assert engine.speak("hello")
            mock_sounddevice.play.assert_called_once()

    def test_speak_returns_false_on_synth_failure(self):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=False):
            assert not engine.speak("hello")

    def test_speak_returns_false_on_playback_failure(self, mock_kokoro, mock_sounddevice):
        mock_sounddevice.play.side_effect = RuntimeError("no audio device")
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            assert not engine.speak("hello")

    def test_model_stays_warm(self, mock_kokoro, mock_sounddevice):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            engine.speak("first")
            engine.speak("second")
            assert mock_kokoro.create.call_count == 2

    def test_voice_and_speed_passed_through(self, mock_kokoro, mock_sounddevice):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            engine.speak("test", voice="af_heart", speed=1.5)
            mock_kokoro.create.assert_called_once_with(
                "test", voice="af_heart", speed=1.5, lang="en-us"
            )

    def test_get_voices(self, mock_kokoro, mock_sounddevice):
        mock_kokoro.get_voices.return_value = ["am_michael", "af_heart", "bf_emma"]
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            voices = engine.get_voices()
            assert voices == ["af_heart", "am_michael", "bf_emma"]

    def test_get_voices_returns_none_when_model_unavailable(self):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=False):
            assert engine.get_voices() is None
