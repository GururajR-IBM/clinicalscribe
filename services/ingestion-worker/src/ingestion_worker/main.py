"""Ingestion worker — Phase 1 implementation.

Pipeline per encounter:
  1. Poll Postgres for `status = 'pending'` (SELECT FOR UPDATE SKIP LOCKED)
  2. Download audio blob from Azure Storage
  3. Transcribe with Azure OpenAI Whisper
  4. Write transcript to Postgres (`status = 'transcribing'` → mark done)
  5. POST to orchestrator to generate SOAP draft (`status = 'drafting'`)
  6. Mark encounter `complete` or `failed`

Phase 2 will replace the Postgres poll loop with Service Bus consumption.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

import httpx
import structlog

from ingestion_worker import __version__
from ingestion_worker.blob import download_blob_to_tempfile
from ingestion_worker.config import settings
from ingestion_worker.db import (
    EncounterStatus,
    claim_pending_encounter,
    ensure_schema,
    get_pool,
    update_encounter,
)
from ingestion_worker.speech import transcribe

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level.upper())
    ),
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


async def _process_encounter(pool, row: dict) -> None:
    encounter_id: uuid.UUID = row["encounter_id"]
    blob_name: str = row.get("blob_name") or f"{encounter_id}/audio"
    log.info("processing_encounter", encounter_id=str(encounter_id), blob=blob_name)

    audio_path: Path | None = None
    try:
        # ── Step 1: Download audio ────────────────────────────────────────
        audio_path = await download_blob_to_tempfile(blob_name)

        # ── Step 2: Transcribe ────────────────────────────────────────────
        transcript = await transcribe(audio_path)
        log.info("transcribed", encounter_id=str(encounter_id), chars=len(transcript))

        await update_encounter(
            pool,
            encounter_id=encounter_id,
            status=EncounterStatus.DRAFTING,
            transcript=transcript,
        )

        # ── Step 3: Call orchestrator for SOAP draft ──────────────────────
        async with httpx.AsyncClient(
            base_url=settings.orchestrator_base_url,
            timeout=settings.orchestrator_timeout_seconds,
        ) as client:
            resp = await client.post(
                "/draft",
                json={
                    "encounter_id": str(encounter_id),
                    "patient_id": row.get("patient_id", ""),
                    "transcript": transcript,
                    "notes": row.get("notes"),
                },
            )
            resp.raise_for_status()
            soap_draft = resp.json()

        await update_encounter(
            pool,
            encounter_id=encounter_id,
            status=EncounterStatus.COMPLETE,
            soap_draft=soap_draft,
        )
        log.info("encounter_complete", encounter_id=str(encounter_id))

    except Exception as exc:
        log.error("encounter_failed", encounter_id=str(encounter_id), error=str(exc))
        await update_encounter(
            pool,
            encounter_id=encounter_id,
            status=EncounterStatus.FAILED,
            error_message=str(exc),
        )
    finally:
        if audio_path and audio_path.exists():
            audio_path.unlink(missing_ok=True)


async def run() -> None:
    log.info("worker_starting", version=__version__, poll_interval=settings.poll_interval_seconds)

    # Postgres is optional in local dev; skip if DATABASE_URL is a placeholder
    try:
        pool = await get_pool()
        await ensure_schema(pool)
        log.info("db_connected")
    except Exception as exc:
        log.warning("db_unavailable", error=str(exc), detail="running in no-db mode")
        pool = None

    while True:
        try:
            if pool:
                row = await claim_pending_encounter(pool)
                if row:
                    await _process_encounter(pool, row)
                    continue  # immediately check for more work
        except Exception as exc:
            log.error("poll_error", error=str(exc))

        await asyncio.sleep(settings.poll_interval_seconds)


def main() -> int:
    try:
        asyncio.run(run())
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())

