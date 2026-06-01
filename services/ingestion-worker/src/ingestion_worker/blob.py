"""Azure Blob Storage download helper for the ingestion-worker.

Downloads encounter audio to a temp file for transcription.
Falls back gracefully when no connection string is set (local dev).
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path

from ingestion_worker.config import settings

log = logging.getLogger(__name__)


async def download_blob_to_tempfile(blob_name: str) -> Path:
    """Download a blob and return the path to a temporary file.

    The caller is responsible for deleting the file after use.
    In local dev (no connection string), writes a 1-second silent WAV stub.
    """
    if not settings.azure_storage_connection_string:
        log.warning("No Azure storage connection string — using silent audio stub for local dev")
        return _write_silent_wav_stub()

    from azure.storage.blob import BlobServiceClient

    service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    container = service.get_container_client(settings.azure_storage_container_encounter_media)
    blob = container.get_blob_client(blob_name)

    tmp = tempfile.NamedTemporaryFile(suffix=".audio", delete=False)
    try:
        stream = blob.download_blob(max_concurrency=4)
        stream.readinto(tmp)
    finally:
        tmp.close()

    return Path(tmp.name)


def _write_silent_wav_stub() -> Path:
    """Return a path to a minimal valid WAV file (1 second silence at 16 kHz mono)."""
    import struct
    import wave

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)  # 1 second of silence
    return Path(tmp.name)
