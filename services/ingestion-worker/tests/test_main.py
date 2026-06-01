"""Tests for the ingestion-worker."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_silent_wav_stub_is_valid_wav() -> None:
    """blob.py generates a valid WAV file when no Azure creds are present."""
    from ingestion_worker.blob import _write_silent_wav_stub

    path = _write_silent_wav_stub()
    assert path.exists()
    assert path.stat().st_size > 44  # WAV header is 44 bytes
    path.unlink()


def test_transcribe_returns_stub_without_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """speech.transcribe returns the stub transcript when AOAI key is empty."""
    monkeypatch.setenv("AOAI_KEY", "")

    # Reload the module so the env var takes effect on settings
    import importlib
    import ingestion_worker.config as cfg_mod
    importlib.reload(cfg_mod)
    import ingestion_worker.speech as speech_mod
    importlib.reload(speech_mod)

    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 512)

    result = asyncio.run(speech_mod.transcribe(wav))
    assert len(result) > 10
    assert "cough" in result.lower() or "pneumonia" in result.lower()


def test_transcribe_rejects_oversized_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """speech.transcribe raises ValueError for files exceeding the size limit."""
    monkeypatch.setenv("AOAI_KEY", "fake-key-so-stub-path-is-skipped")

    import importlib
    import ingestion_worker.config as cfg_mod
    importlib.reload(cfg_mod)
    import ingestion_worker.speech as speech_mod
    importlib.reload(speech_mod)

    big_file = tmp_path / "big.wav"
    # Write a file just over the 25 MB limit
    big_file.write_bytes(b"\x00" * (26 * 1024 * 1024))

    with pytest.raises(ValueError, match="exceeds"):
        asyncio.run(speech_mod.transcribe(big_file))

