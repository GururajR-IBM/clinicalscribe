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
    soap_final: dict | None = None,
    error_message: str | None = None,
    cosmos_run_id: uuid.UUID | None = None,
) -> None:
    import json

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE encounters
               SET status        = $1,
                   transcript    = COALESCE($2, transcript),
                   soap_draft    = COALESCE($3::jsonb, soap_draft),
                   soap_final    = COALESCE($4::jsonb, soap_final),
                   error_message = COALESCE($5, error_message),
                   cosmos_run_id = COALESCE($6, cosmos_run_id),
                   updated_at    = now()
             WHERE encounter_id = $7
            """,
            status,
            transcript,
            json.dumps(soap_draft) if soap_draft else None,
            json.dumps(soap_final) if soap_final else None,
            error_message,
            cosmos_run_id,
            encounter_id,
        )


async def insert_codes(
    pool: asyncpg.Pool,
    *,
    encounter_id: uuid.UUID,
    codes: list[dict],
) -> None:
    """Bulk-insert suggested codes from the Coder agent."""
    import json

    if not codes:
        return
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO codes (encounter_id, code, code_type, description, confidence, justification)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    encounter_id,
                    c.get("code", ""),
                    c.get("code_type", "icd10"),
                    c.get("description", ""),
                    c.get("confidence", "low"),
                    c.get("justification", ""),
                )
                for c in codes
            ],
        )


async def insert_drug_warnings(
    pool: asyncpg.Pool,
    *,
    encounter_id: uuid.UUID,
    warnings: list[dict],
) -> None:
    """Bulk-insert drug interaction warnings."""
    if not warnings:
        return
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO drug_interaction_warnings (encounter_id, drugs, severity, description)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    encounter_id,
                    w.get("drugs", []),
                    w.get("severity", "unknown"),
                    w.get("description", ""),
                )
                for w in warnings
            ],
        )

