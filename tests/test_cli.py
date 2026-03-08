"""Unit tests for speaker CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from typer.testing import CliRunner

from speaker.cli import (
    _ensure_models,
    _load_config,
    _speak_kokoro,
    _speak_macos,
    app,
)

runner = CliRunner()


# --- _load_config ---


class TestLoadConfig:
    def test_missing_file(self, monkeypatch):
        monkeypatch.setattr("speaker.cli._CONFIG_PATH", Path("/nonexistent/config.yaml"))
        assert _load_config() == {}

    def test_valid(self, tmp_config, monkeypatch):
        monkeypatch.setattr("speaker.cli._CONFIG_PATH", tmp_config)
        cfg = _load_config()
        assert cfg["voice"] == "af_heart"
        assert cfg["speed"] == 1.2
        assert cfg["macos_voice"] == "Daniel"

    def test_invalid_yaml(self, tmp_path, monkeypatch):
        bad = tmp_path / "config.yaml"
        bad.write_text(": : :\n  - [invalid")
        monkeypatch.setattr("speaker.cli._CONFIG_PATH", bad)
        assert _load_config() == {}


# --- _ensure_models ---


class TestEnsureModels:
    def test_already_exist(self, monkeypatch):
        monkeypatch.setattr("speaker.cli._KOKORO_MODEL", MagicMock(exists=lambda: True))
        monkeypatch.setattr("speaker.cli._KOKORO_VOICES", MagicMock(exists=lambda: True))
        assert _ensure_models() is True

    def test_downloads(self, tmp_path, monkeypatch):
        model = tmp_path / "kokoro-v1.0.onnx"
        voices = tmp_path / "voices-v1.0.bin"
        monkeypatch.setattr("speaker.cli._KOKORO_DIR", tmp_path)
        monkeypatch.setattr("speaker.cli._KOKORO_MODEL", model)
        monkeypatch.setattr("speaker.cli._KOKORO_VOICES", voices)

        def fake_run(cmd, **kwargs):
            # Simulate wget creating the file
            Path(cmd[-1]).touch()

        monkeypatch.setattr("speaker.cli.subprocess.run", fake_run)
        assert _ensure_models() is True
        assert model.exists()
        assert voices.exists()


# --- _speak_kokoro ---


class TestSpeakKokoro:
    def test_success(self, monkeypatch, mock_kokoro, mock_sounddevice):
        monkeypatch.setattr("speaker.cli._ensure_models", lambda: True)
        # Need numpy available as real module
        monkeypatch.setitem(sys.modules, "numpy", np)

        result = _speak_kokoro("hello", voice="am_michael", speed=1.0)
        assert result is True
        mock_kokoro.create.assert_called_once_with(
            "hello", voice="am_michael", speed=1.0, lang="en-us"
        )
        mock_sounddevice.play.assert_called_once()
        mock_sounddevice.wait.assert_called_once()

    def test_resampling(self, monkeypatch, mock_kokoro, mock_sounddevice):
        """Verify 24kHz→48kHz resampling: output should have ~2x samples."""
        monkeypatch.setattr("speaker.cli._ensure_models", lambda: True)
        monkeypatch.setitem(sys.modules, "numpy", np)

        fake_samples = np.zeros(2400, dtype=np.float32)
        mock_kokoro.create.return_value = (fake_samples, 24000)

        _speak_kokoro("test", voice="am_michael", speed=1.0)

        played_samples = mock_sounddevice.play.call_args[0][0]
        played_sr = mock_sounddevice.play.call_args[0][1]
        assert played_sr == 48000
        assert len(played_samples) == pytest.approx(4800, abs=1)

    def test_import_error(self, monkeypatch):
        """Returns False when kokoro_onnx not installed."""
        # Remove mocked modules so import fails
        monkeypatch.delitem(sys.modules, "kokoro_onnx", raising=False)
        monkeypatch.delitem(sys.modules, "sounddevice", raising=False)

        # Force ImportError by patching builtins.__import__
        original_import = (
            __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
        )

        def fail_import(name, *args, **kwargs):
            if name in ("kokoro_onnx", "sounddevice"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fail_import)
        result = _speak_kokoro("hello", voice="am_michael", speed=1.0)
        assert result is False


# --- _speak_macos ---


class TestSpeakMacos:
    def test_success(self, monkeypatch):
        monkeypatch.setattr("speaker.cli.subprocess.run", lambda *a, **kw: None)
        assert _speak_macos("hello", voice="Samantha") is True

    def test_failure(self, monkeypatch):
        def raise_err(*a, **kw):
            raise subprocess.CalledProcessError(1, "say")

        monkeypatch.setattr("speaker.cli.subprocess.run", raise_err)
        assert _speak_macos("hello", voice="Samantha") is False


# --- CLI integration via CliRunner ---


class TestCLI:
    def test_empty_text(self, monkeypatch):
        """Empty string after stripping should return without speaking."""
        monkeypatch.setattr("speaker.cli._load_config", lambda: {})
        result = runner.invoke(app, [""])
        assert result.exit_code == 0

    def test_stdin(self, monkeypatch):
        """Test reading from stdin with '-' argument."""
        spoken = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {"backend": "kokoro"})
        monkeypatch.setattr(
            "speaker.cli._speak_kokoro", lambda t, **kw: (spoken.append(t), True)[1]
        )
        result = runner.invoke(app, ["-"], input="hello from stdin\n")
        assert result.exit_code == 0
        assert spoken == ["hello from stdin"]

    def test_backend_selection_macos(self, monkeypatch):
        """'-b macos' forces macOS backend."""
        spoken = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {})
        monkeypatch.setattr("speaker.cli._speak_macos", lambda t, **kw: (spoken.append(t), True)[1])
        result = runner.invoke(app, ["hello", "-b", "macos"])
        assert result.exit_code == 0
        assert spoken == ["hello"]

    def test_voice_override(self, monkeypatch):
        """'-v' flag overrides config voice."""
        calls = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {"voice": "am_michael"})
        monkeypatch.setattr(
            "speaker.cli._speak_kokoro",
            lambda t, voice, speed: (calls.append(voice), True)[1],
        )
        runner.invoke(app, ["hello", "-v", "af_heart"])
        assert calls == ["af_heart"]

    def test_speed_override(self, monkeypatch):
        """'-s' flag overrides config speed."""
        calls = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {"speed": 1.0})
        monkeypatch.setattr(
            "speaker.cli._speak_kokoro",
            lambda t, voice, speed: (calls.append(speed), True)[1],
        )
        runner.invoke(app, ["hello", "-s", "1.5"])
        assert calls == [1.5]

    def test_kokoro_fallback_to_macos(self, monkeypatch):
        """When kokoro fails, falls back to macOS say."""
        macos_calls = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {})
        monkeypatch.setattr("speaker.cli._speak_kokoro", lambda t, **kw: False)
        monkeypatch.setattr(
            "speaker.cli._speak_macos",
            lambda t, **kw: (macos_calls.append(t), True)[1],
        )
        result = runner.invoke(app, ["hello"])
        assert result.exit_code == 0
        assert macos_calls == ["hello"]
