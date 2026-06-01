"""Encounter state persistence for the ingestion-worker (SQLite via aiosqlite).

Default is a local SQLite file -- zero infra, work-laptop friendly,
FIPS-validatable, and HIPAA-compatible when the file lives on encrypted
storage. The same public API can be backed by Postgres later by swapping
``database_url`` and the driver -- the row shapes are identical.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import aiosqlite

from ingestion_worker.config import settings


class EncounterStatus(StrEnum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    DRAFTING = "drafting"
    COMPLETE = "complete"
    FAILED = "failed"


_CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS encounters (
        encounter_id   TEXT PRIMARY KEY,
        user_id        TEXT NOT NULL,
        patient_id     TEXT NOT NULL,
        status         TEXT NOT NULL DEFAULT 'pending',
        notes          TEXT,
        blob_name      TEXT,
        transcript     TEXT,
        soap_draft     TEXT,
        soap_final     TEXT,
        error_message  TEXT,
        cosmos_run_id  TEXT,
        created_at     TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS codes (
        code_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        encounter_id   TEXT NOT NULL,
        code           TEXT NOT NULL,
        code_type      TEXT NOT NULL,
        description    TEXT,
        confidence     TEXT,
        justification  TEXT,
        UNIQUE(encounter_id, code, code_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS drug_interaction_warnings (
        warning_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        encounter_id   TEXT NOT NULL,
        drugs          TEXT NOT NULL,
        severity       TEXT NOT NULL,
        description    TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_encounters_status ON encounters(status, created_at)",
]


def _sqlite_path() -> str:
    """Extract the SQLite file path from settings.database_url."""
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    if url.startswith("sqlite+aiosqlite:///"):
        return url[len("sqlite+aiosqlite:///"):]
    # Plain path
    return url


async def get_pool() -> str:
    """Return the SQLite database path. Kept as ``get_pool`` for API parity with the prior asyncpg version."""
    return _sqlite_path()


async def ensure_schema(pool: str) -> None:
    async with aiosqlite.connect(pool) as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        for ddl in _CREATE_TABLES_SQL:
            await conn.execute(ddl)
        await conn.commit()


async def claim_pending_encounter(pool: str) -> dict | None:
    """Atomically claim one pending encounter for processing."""
    async with aiosqlite.connect(pool) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("BEGIN IMMEDIATE")
        cursor = await conn.execute(
            "SELECT encounter_id, user_id, patient_id, blob_name, notes "
            "FROM encounters WHERE status = 'pending' ORDER BY created_at LIMIT 1"
        )
        row = await cursor.fetchone()
        if row is None:
            await conn.commit()
            return None
        await conn.execute(
            "UPDATE encounters SET status = ?, updated_at = datetime('now') WHERE encounter_id = ?",
            (EncounterStatus.TRANSCRIBING.value, row["encounter_id"]),
        )
        await conn.commit()
    return {
        "encounter_id": uuid.UUID(row["encounter_id"]),
        "user_id": row["user_id"],
        "patient_id": row["patient_id"],
        "blob_name": row["blob_name"],
        "notes": row["notes"],
    }


async def update_encounter(
    pool: str,
    *,
    encounter_id: uuid.UUID,
    status: EncounterStatus,
    transcript: str | None = None,
    soap_draft: dict | None = None,
    soap_final: dict | None = None,
    error_message: str | None = None,
    cosmos_run_id: uuid.UUID | None = None,
) -> None:
    fields: list[str] = ["status = ?", "updated_at = datetime('now')"]
    values: list[Any] = [status.value]
    if transcript is not None:
        fields.append("transcript = ?")
        values.append(transcript)
    if soap_draft is not None:
        fields.append("soap_draft = ?")
        values.append(json.dumps(soap_draft))
    if soap_final is not None:
        fields.append("soap_final = ?")
        values.append(json.dumps(soap_final))
    if error_message is not None:
        fields.append("error_message = ?")
        values.append(error_message)
    if cosmos_run_id is not None:
        fields.append("cosmos_run_id = ?")
        values.append(str(cosmos_run_id))
    values.append(str(encounter_id))

    async with aiosqlite.connect(pool) as conn:
        await conn.execute(
            f"UPDATE encounters SET {', '.join(fields)} WHERE encounter_id = ?",
            values,
        )
        await conn.commit()


async def insert_codes(pool: str, *, encounter_id: uuid.UUID, codes: list[dict]) -> None:
    if not codes:
        return
    rows = [
        (
            str(encounter_id),
            c.get("code", ""),
            c.get("code_type", "icd10"),
            c.get("description", ""),
            c.get("confidence", "low"),
            c.get("justification", ""),
        )
        for c in codes
    ]
    async with aiosqlite.connect(pool) as conn:
        await conn.executemany(
            "INSERT OR IGNORE INTO codes "
            "(encounter_id, code, code_type, description, confidence, justification) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        await conn.commit()


async def insert_drug_warnings(pool: str, *, encounter_id: uuid.UUID, warnings: list[dict]) -> None:
    if not warnings:
        return
    rows = [
        (
            str(encounter_id),
            json.dumps(w.get("drugs", [])),
            w.get("severity", "unknown"),
            w.get("description", ""),
        )
        for w in warnings
    ]
    async with aiosqlite.connect(pool) as conn:
        await conn.executemany(
            "INSERT INTO drug_interaction_warnings "
            "(encounter_id, drugs, severity, description) VALUES (?, ?, ?, ?)",
            rows,
        )
        await conn.commit()


# -- Test helper ---------------------------------------------------------------
async def insert_pending_encounter(
    pool: str,
    *,
    user_id: str,
    patient_id: str,
    blob_name: str,
    notes: str | None = None,
) -> uuid.UUID:
    """Insert a pending encounter -- useful for local smoke tests."""
    eid = uuid.uuid4()
    async with aiosqlite.connect(pool) as conn:
        await conn.execute(
            "INSERT INTO encounters (encounter_id, user_id, patient_id, blob_name, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(eid), user_id, patient_id, blob_name, notes),
        )
        await conn.commit()
    return eid
