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

    def test_downloads(self, tmp_path, monkeypatch):
        model = tmp_path / "kokoro-v1.0.onnx"
        voices = tmp_path / "voices-v1.0.bin"
        monkeypatch.setattr("speaker.engine._KOKORO_DIR", tmp_path)
        monkeypatch.setattr("speaker.engine._KOKORO_MODEL", model)
        monkeypatch.setattr("speaker.engine._KOKORO_VOICES", voices)

        def fake_run(cmd, **kwargs):
            Path(cmd[-1]).touch()

        monkeypatch.setattr("speaker.engine.subprocess.run", fake_run)
        assert _ensure_models() is True
        assert model.exists()
        assert voices.exists()

    def test_download_failure(self, tmp_path, monkeypatch):
        import subprocess

        monkeypatch.setattr("speaker.engine._KOKORO_DIR", tmp_path)
        monkeypatch.setattr("speaker.engine._KOKORO_MODEL", tmp_path / "kokoro-v1.0.onnx")
        monkeypatch.setattr("speaker.engine._KOKORO_VOICES", tmp_path / "voices-v1.0.bin")

        def fail_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(1, "wget")

        monkeypatch.setattr("speaker.engine.subprocess.run", fail_run)
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
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            engine.load()
            engine.load()
            # Kokoro constructor called only once
            import sys

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
            mock_sounddevice.wait.assert_called_once()

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
            # Kokoro constructor should only be called once (model stays warm)
            assert mock_kokoro.create.call_count == 2

    def test_voice_and_speed_passed_through(self, mock_kokoro, mock_sounddevice):
        engine = SpeakerEngine()
        with patch("speaker.engine._ensure_models", return_value=True):
            engine.speak("test", voice="af_heart", speed=1.5)
            mock_kokoro.create.assert_called_once_with(
                "test", voice="af_heart", speed=1.5, lang="en-us"
            )
