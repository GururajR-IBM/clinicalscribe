"""Azure OpenAI Whisper transcription client.

Phase 1 uses the AOAI Whisper endpoint (same resource as GPT-4o).
The client validates the audio size before upload to avoid
hitting the 25 MB AOAI limit (OWASP A04 — Insecure Design: validate at boundaries).
"""

from __future__ import annotations

import logging
from pathlib import Path

from openai import AsyncAzureOpenAI

from ingestion_worker.config import settings

log = logging.getLogger(__name__)

_client: AsyncAzureOpenAI | None = None


def _get_client() -> AsyncAzureOpenAI:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.aoai_endpoint,
            api_key=settings.aoai_key,
            api_version="2024-06-01",
        )
    return _client


async def transcribe(audio_path: Path) -> str:
    """Transcribe an audio file and return the plain-text transcript.

    Raises ValueError if the file exceeds the AOAI Whisper size limit.
    Returns a stub transcript in local dev when aoai_key is not set.
    """
    size = audio_path.stat().st_size
    if size > settings.max_audio_bytes:
        raise ValueError(
            f"Audio file size {size / 1_048_576:.1f} MB exceeds the "
            f"{settings.max_audio_bytes / 1_048_576:.0f} MB limit."
        )

    if not settings.aoai_key:
        log.warning("No AOAI key — returning stub transcript for local dev")
        return (
            "Patient presents with a 3-day history of productive cough, "
            "low-grade fever, and shortness of breath on exertion. "
            "No prior cardiac history. Assessment: likely community-acquired pneumonia. "
            "Plan: amoxicillin 500 mg TID for 7 days, follow-up in 1 week."
        )

    client = _get_client()
    with open(audio_path, "rb") as f:
        response = await client.audio.transcriptions.create(
            model=settings.aoai_whisper_deployment,
            file=f,
            response_format="text",
        )
    # The openai client returns a plain string for response_format="text"
    return response if isinstance(response, str) else response.text
