"""Unit tests for MCP speaker server."""

from __future__ import annotations

from unittest.mock import patch

from speaker import mcp_server
from speaker.engine import SpeakerEngine
from speaker.mcp_server import speak


class TestMCPSpeak:
    def setup_method(self):
        """Reset module-level engine between tests."""
        mcp_server._engine = SpeakerEngine()

    def test_success(self, mock_kokoro, mock_sounddevice):
        result = speak("hello world")
        assert "Spoke:" in result
        assert "hello world" in result

    def test_empty_text(self):
        result = speak("")
        assert "No text" in result

    def test_whitespace_only(self):
        result = speak("   ")
        assert "No text" in result

    def test_failure(self):
        with patch.object(SpeakerEngine, "speak", return_value=False):
            result = speak("hello")
            assert "TTS failed" in result

    def test_truncates_long_text_in_response(self, mock_kokoro, mock_sounddevice):
        long_text = "x" * 200
        result = speak(long_text)
        assert "Spoke:" in result
        assert len(result) < 200

    def test_voice_and_speed_params(self, mock_kokoro, mock_sounddevice):
        result = speak("test", voice="af_heart", speed=1.5)
        assert "Spoke:" in result
        mock_kokoro.create.assert_called_once_with(
            "test", voice="af_heart", speed=1.5, lang="en-us"
        )

    def test_default_voice_and_speed(self, mock_kokoro, mock_sounddevice):
        speak("test")
        mock_kokoro.create.assert_called_once_with(
            "test", voice="am_michael", speed=1.0, lang="en-us"
        )
