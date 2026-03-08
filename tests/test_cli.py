"""Unit tests for speaker CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from speaker.cli import _load_config, _speak_macos, app
from speaker.engine import SpeakerEngine

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

    def test_timeout(self, monkeypatch):
        def raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired("say", 60)

        monkeypatch.setattr("speaker.cli.subprocess.run", raise_timeout)
        assert _speak_macos("hello", voice="Samantha") is False

    def test_missing_say(self, monkeypatch):
        def raise_fnf(*a, **kw):
            raise FileNotFoundError("say")

        monkeypatch.setattr("speaker.cli.subprocess.run", raise_fnf)
        assert _speak_macos("hello", voice="Samantha") is False


# --- CLI integration via CliRunner ---


class TestCLI:
    def test_empty_text(self, monkeypatch):
        monkeypatch.setattr("speaker.cli._load_config", lambda: {})
        result = runner.invoke(app, [""])
        assert result.exit_code == 0

    def test_stdin(self, monkeypatch):
        spoken = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {"backend": "kokoro"})
        monkeypatch.setattr(
            SpeakerEngine, "speak", lambda self, t, **kw: (spoken.append(t), True)[1]
        )
        result = runner.invoke(app, ["-"], input="hello from stdin\n")
        assert result.exit_code == 0
        assert spoken == ["hello from stdin"]

    def test_backend_selection_macos(self, monkeypatch):
        spoken = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {})
        monkeypatch.setattr("speaker.cli._speak_macos", lambda t, **kw: (spoken.append(t), True)[1])
        result = runner.invoke(app, ["hello", "-b", "macos"])
        assert result.exit_code == 0
        assert spoken == ["hello"]

    def test_voice_override(self, monkeypatch):
        calls = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {"voice": "am_michael"})
        monkeypatch.setattr(
            SpeakerEngine,
            "speak",
            lambda self, t, voice="am_michael", speed=1.0: (calls.append(voice), True)[1],
        )
        runner.invoke(app, ["hello", "-v", "af_heart"])
        assert calls == ["af_heart"]

    def test_speed_override(self, monkeypatch):
        calls = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {"speed": 1.0})
        monkeypatch.setattr(
            SpeakerEngine,
            "speak",
            lambda self, t, voice="am_michael", speed=1.0: (calls.append(speed), True)[1],
        )
        runner.invoke(app, ["hello", "-s", "1.5"])
        assert calls == [1.5]

    def test_kokoro_fallback_to_macos(self, monkeypatch):
        macos_calls = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {})
        monkeypatch.setattr(SpeakerEngine, "speak", lambda self, t, **kw: False)
        monkeypatch.setattr(
            "speaker.cli._speak_macos",
            lambda t, **kw: (macos_calls.append(t), True)[1],
        )
        result = runner.invoke(app, ["hello"])
        assert result.exit_code == 0
        assert macos_calls == ["hello"]

    def test_config_defaults_used(self, monkeypatch):
        """When no flags or config, defaults should be used."""
        calls = []
        monkeypatch.setattr("speaker.cli._load_config", lambda: {})
        monkeypatch.setattr(
            SpeakerEngine,
            "speak",
            lambda self, t, voice="am_michael", speed=1.0: (
                calls.append({"voice": voice, "speed": speed}),
                True,
            )[1],
        )
        runner.invoke(app, ["hello"])
        assert calls == [{"voice": "am_michael", "speed": 1.0}]

    def test_config_values_used(self, tmp_config, monkeypatch):
        """Config file values should be used when no CLI flags provided."""
        calls = []
        monkeypatch.setattr("speaker.cli._CONFIG_PATH", tmp_config)
        monkeypatch.setattr(
            SpeakerEngine,
            "speak",
            lambda self, t, voice="am_michael", speed=1.0: (
                calls.append({"voice": voice, "speed": speed}),
                True,
            )[1],
        )
        runner.invoke(app, ["hello"])
        assert calls == [{"voice": "af_heart", "speed": 1.2}]

    def test_no_text_no_stdin_exits(self):
        """Calling with no text and no stdin should show usage."""
        result = runner.invoke(app, [])
        # typer shows help or exits cleanly with no args
        assert result.exit_code == 0 or "Usage" in result.output
