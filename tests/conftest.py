"""Shared fixtures for speaker tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture()
def tmp_config(tmp_path):
    """Create a temporary config.yaml with test values."""
    config = tmp_path / "config.yaml"
    config.write_text(
        "tts:\n  voice: af_heart\n  speed: 1.2\n  backend: kokoro\n  macos_voice: Daniel\n"
    )
    return config


@pytest.fixture()
def mock_kokoro(monkeypatch):
    """Patch kokoro_onnx.Kokoro to return fake samples."""
    fake_samples = np.zeros(4800, dtype=np.float32)
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_instance.create.return_value = (fake_samples, 24000)
    mock_cls.return_value = mock_instance

    mod = MagicMock()
    mod.Kokoro = mock_cls
    monkeypatch.setitem(sys.modules, "kokoro_onnx", mod)
    return mock_instance


@pytest.fixture()
def mock_sounddevice(monkeypatch):
    """Patch sounddevice.play and sounddevice.wait."""
    mod = MagicMock()
    monkeypatch.setitem(sys.modules, "sounddevice", mod)
    return mod
