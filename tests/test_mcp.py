"""Unit tests for MCP speaker server."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


# Import the speak function directly from the server module
import importlib.util

_SERVER_PATH = Path(__file__).parent.parent / "agents" / "mcp" / "speaker-server.py"


@pytest.fixture()
def speak_fn():
    """Import speak function from the MCP server script."""
    spec = importlib.util.spec_from_file_location("speaker_server", _SERVER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.speak


@pytest.fixture()
def speak_bin():
    """Import _SPEAK_BIN from the MCP server script."""
    spec = importlib.util.spec_from_file_location("speaker_server", _SERVER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._SPEAK_BIN


class TestMCPSpeak:
    def test_success(self, speak_fn):
        with patch("subprocess.run") as mock_run:
            result = speak_fn("hello world")
            assert "🔊 Spoke:" in result
            assert "hello world" in result
            mock_run.assert_called_once()

    def test_failure(self, speak_fn):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "speak")):
            result = speak_fn("hello")
            assert "TTS failed" in result

    def test_timeout(self, speak_fn):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("speak", 120)):
            result = speak_fn("hello")
            assert "TTS failed" in result

    def test_not_found(self, speak_fn):
        with patch("subprocess.run", side_effect=FileNotFoundError("speak not found")):
            result = speak_fn("hello")
            assert "TTS failed" in result

    def test_speak_bin_path(self, speak_bin):
        expected = Path.home() / ".local" / "bin" / "speak"
        assert speak_bin == expected
