"""In-memory encounter store for local dev / testing.

Swapped for a real asyncpg-backed store when DATABASE_URL is configured.
This lets the service run and be tested without a live Postgres instance.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request

from gateway.schemas import EncounterResponse, EncounterStatus


class EncounterStore:
    """Thin persistence abstraction over encounter rows."""

    def __init__(self) -> None:
        # In-process dict for local dev; replaced by asyncpg pool in production.
        self._rows: dict[uuid.UUID, dict] = {}

    async def create(
        self,
        *,
        encounter_id: uuid.UUID,
        user_id: str,
        patient_id: str,
        notes: str | None,
        blob_name: str,
    ) -> None:
        now = datetime.now(UTC)
        self._rows[encounter_id] = {
            "encounter_id": encounter_id,
            "user_id": user_id,
            "patient_id": patient_id,
            "status": EncounterStatus.PENDING,
            "notes": notes,
            "blob_name": blob_name,
            "soap_draft": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }

    async def get(self, *, encounter_id: uuid.UUID, user_id: str) -> EncounterResponse | None:
        row = self._rows.get(encounter_id)
        if row is None or row["user_id"] != user_id:
            return None
        return EncounterResponse(**row)

    async def update_status(
        self,
        *,
        encounter_id: uuid.UUID,
        status: EncounterStatus,
        soap_draft: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        row = self._rows.get(encounter_id)
        if row is None:
            return
        row["status"] = status
        row["updated_at"] = datetime.now(UTC)
        if soap_draft is not None:
            row["soap_draft"] = soap_draft
        if error_message is not None:
            row["error_message"] = error_message


# Singleton for local dev (one store per process lifetime)
_store = EncounterStore()


def get_store(request: Request) -> EncounterStore:  # noqa: ARG001
    """FastAPI dependency: returns the app-level store.

    In production this will return an asyncpg-backed store attached to
    `request.app.state.store` during startup.
    """
    return _store


# Annotated dependency alias used in route signatures
EncounterStore = Annotated[EncounterStore, Depends(get_store)]  # type: ignore[misc]
