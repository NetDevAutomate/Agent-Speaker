"""Shared fixtures for speaker tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture()
def mock_kokoro(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch kokoro_onnx.Kokoro to return fake samples."""
    fake_samples = np.zeros(4800, dtype=np.float32)
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_instance.create.return_value = (fake_samples, 24000)
    mock_cls.return_value = mock_instance

    mod = MagicMock()
    mod.Kokoro = mock_cls
    monkeypatch.setitem(sys.modules, "kokoro_onnx", mod)
    monkeypatch.setattr("speaker.engine._ensure_models", lambda: True)
    return mock_instance


@pytest.fixture()
def mock_sounddevice(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch sounddevice.play and sounddevice.wait."""
    mod = MagicMock()
    monkeypatch.setitem(sys.modules, "sounddevice", mod)
    return mod
