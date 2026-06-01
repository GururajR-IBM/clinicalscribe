"""Encounter API routes — POST /encounters, GET /encounters/{id}, SSE events.

Phase 1 scope (task 1.10 + 1.11):
- POST /encounters  : create encounter row, issue signed Blob upload URL
- GET  /encounters/{id} : fetch encounter state
- GET  /encounters/{id}/events : SSE stream for live progress

Storage is abstracted behind thin helpers so the real Azure Blob client
can be swapped for Azurite (local emulator) by changing the connection string.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from gateway.auth import CurrentUser
from gateway.schemas import (
    CreateEncounterRequest,
    CreateEncounterResponse,
    EncounterResponse,
    EncounterStatus,
)
from gateway.storage import generate_upload_sas_url
from gateway.store import EncounterStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/encounters", tags=["encounters"])

# ---------------------------------------------------------------------------
# POST /encounters
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=CreateEncounterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new encounter and get a signed upload URL",
)
async def create_encounter(
    body: CreateEncounterRequest,
    user: CurrentUser,
    store: EncounterStore,
) -> CreateEncounterResponse:
    """Create an encounter record and return a pre-signed Blob upload URL.

    The client should PUT the audio file directly to `upload_url`.
    The ingestion worker polls for `status=pending` rows and processes them.
    """
    user_id: str = user.get("sub", "unknown")
    encounter_id = uuid.uuid4()
    blob_name = f"{encounter_id}/audio"

    upload_url, expires_at = await generate_upload_sas_url(
        blob_name=blob_name,
        content_type=body.content_type,
        ttl_minutes=15,
    )

    await store.create(
        encounter_id=encounter_id,
        user_id=user_id,
        patient_id=body.patient_id,
        notes=body.notes,
        blob_name=blob_name,
    )

    return CreateEncounterResponse(
        encounter_id=encounter_id,
        upload_url=upload_url,
        upload_expires_at=expires_at,
        status=EncounterStatus.PENDING,
    )


# ---------------------------------------------------------------------------
# GET /encounters/{encounter_id}
# ---------------------------------------------------------------------------


@router.get(
    "/{encounter_id}",
    response_model=EncounterResponse,
    summary="Get encounter status and SOAP draft",
)
async def get_encounter(
    encounter_id: uuid.UUID,
    user: CurrentUser,
    store: EncounterStore,
) -> EncounterResponse:
    user_id: str = user.get("sub", "unknown")
    row = await store.get(encounter_id=encounter_id, user_id=user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")
    return row


# ---------------------------------------------------------------------------
# GET /encounters/{encounter_id}/events  (SSE)
# ---------------------------------------------------------------------------


@router.get(
    "/{encounter_id}/events",
    summary="Server-sent events stream for encounter progress",
    response_class=EventSourceResponse,
)
async def encounter_events(
    encounter_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    store: EncounterStore,
) -> EventSourceResponse:
    """Stream encounter status updates to the browser using Server-Sent Events.

    Clients receive a `status_change` event each time the encounter moves
    through the pipeline (pending → transcribing → drafting → complete).
    The stream closes automatically when `complete` or `failed` is reached,
    or when the client disconnects.
    """
    user_id: str = user.get("sub", "unknown")

    async def _generator():
        last_status: str | None = None
        poll_interval = 2.0  # seconds

        while True:
            if await request.is_disconnected():
                break

            row = await store.get(encounter_id=encounter_id, user_id=user_id)
            if row is None:
                yield {
                    "event": "error",
                    "data": json.dumps({"detail": "Encounter not found."}),
                }
                break

            current_status = row.status
            if current_status != last_status:
                last_status = current_status
                payload = {
                    "encounter_id": str(encounter_id),
                    "status": current_status,
                    "updated_at": row.updated_at.isoformat(),
                }
                if current_status == EncounterStatus.COMPLETE:
                    payload["soap_draft"] = row.soap_draft
                yield {"event": "status_change", "data": json.dumps(payload)}

            if current_status in (EncounterStatus.COMPLETE, EncounterStatus.FAILED):
                break

            await asyncio.sleep(poll_interval)

    return EventSourceResponse(_generator())
