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

    def test_short_text_no_ellipsis(self, mock_kokoro, mock_sounddevice):
        result = speak("short")
        assert result == "Spoke: short"

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


class TestInputValidation:
    def setup_method(self):
        mcp_server._engine = SpeakerEngine()

    def test_invalid_voice_rejected(self):
        result = speak("hello", voice="../../etc/passwd")
        assert "Invalid voice" in result

    def test_invalid_voice_with_spaces(self):
        result = speak("hello", voice="Samantha -o /tmp/evil")
        assert "Invalid voice" in result

    def test_invalid_voice_uppercase(self):
        result = speak("hello", voice="AM_MICHAEL")
        assert "Invalid voice" in result

    def test_valid_voice_accepted(self, mock_kokoro, mock_sounddevice):
        result = speak("hello", voice="bf_emma")
        assert "Spoke:" in result

    def test_speed_clamped_high(self, mock_kokoro, mock_sounddevice):
        speak("test", speed=5.0)
        mock_kokoro.create.assert_called_once_with(
            "test", voice="am_michael", speed=2.0, lang="en-us"
        )

    def test_speed_clamped_low(self, mock_kokoro, mock_sounddevice):
        speak("test", speed=0.1)
        mock_kokoro.create.assert_called_once_with(
            "test", voice="am_michael", speed=0.5, lang="en-us"
        )

    def test_text_truncated_at_limit(self, mock_kokoro, mock_sounddevice):
        huge_text = "a" * 20_000
        speak(huge_text)
        actual_text = mock_kokoro.create.call_args[0][0]
        assert len(actual_text) == 10_000

    def test_text_under_limit_not_truncated(self, mock_kokoro, mock_sounddevice):
        text = "a" * 5000
        speak(text)
        actual_text = mock_kokoro.create.call_args[0][0]
        assert len(actual_text) == 5000
