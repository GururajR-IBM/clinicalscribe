"""Encounter state persistence for the ingestion-worker.

Phase 1 uses a direct asyncpg connection; Phase 2 swaps this for
Service Bus consumption. The SQL schema is kept inline here so
the worker is self-contained and easy to reason about.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

import asyncpg

from ingestion_worker.config import settings


class EncounterStatus(StrEnum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    DRAFTING = "drafting"
    COMPLETE = "complete"
    FAILED = "failed"


# DDL executed once at startup to guarantee the table exists.
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS encounters (
    encounter_id    UUID PRIMARY KEY,
    user_id         TEXT        NOT NULL,
    patient_id      TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'pending',
    notes           TEXT,
    blob_name       TEXT,
    soap_draft      JSONB,
    error_message   TEXT,
    transcript      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


async def get_pool() -> asyncpg.Pool:
    """Create a connection pool. Call once at worker startup."""
    return await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)


async def ensure_schema(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_TABLE_SQL)


async def claim_pending_encounter(pool: asyncpg.Pool) -> dict | None:
    """Atomically claim one pending encounter for processing (SELECT FOR UPDATE SKIP LOCKED)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE encounters
               SET status     = $1,
                   updated_at = now()
             WHERE encounter_id = (
                SELECT encounter_id
                  FROM encounters
                 WHERE status = 'pending'
                 ORDER BY created_at
                 LIMIT 1
                   FOR UPDATE SKIP LOCKED
             )
             RETURNING encounter_id, user_id, patient_id, blob_name, notes
            """,
            EncounterStatus.TRANSCRIBING,
        )
    return dict(row) if row else None


async def update_encounter(
    pool: asyncpg.Pool,
    *,
    encounter_id: uuid.UUID,
    status: EncounterStatus,
    transcript: str | None = None,
    soap_draft: dict | None = None,
    error_message: str | None = None,
) -> None:
    import json

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE encounters
               SET status        = $1,
                   transcript    = COALESCE($2, transcript),
                   soap_draft    = COALESCE($3::jsonb, soap_draft),
                   error_message = COALESCE($4, error_message),
                   updated_at    = now()
             WHERE encounter_id = $5
            """,
            status,
            transcript,
            json.dumps(soap_draft) if soap_draft else None,
            error_message,
            encounter_id,
        )
