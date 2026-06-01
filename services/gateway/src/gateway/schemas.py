"""Pydantic schemas for the encounters API."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EncounterStatus(StrEnum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    DRAFTING = "drafting"
    COMPLETE = "complete"
    FAILED = "failed"


class CreateEncounterRequest(BaseModel):
    patient_id: str = Field(..., description="Opaque patient reference (de-identified)")
    notes: str | None = Field(None, max_length=2000, description="Optional clinician notes")
    content_type: str = Field(
        "audio/mpeg",
        description="MIME type of the audio file to be uploaded (e.g. audio/mpeg, audio/wav)",
    )


class CreateEncounterResponse(BaseModel):
    encounter_id: uuid.UUID
    upload_url: str = Field(..., description="Pre-signed Blob URL for the audio upload (PUT)")
    upload_expires_at: datetime
    status: EncounterStatus


class EncounterResponse(BaseModel):
    encounter_id: uuid.UUID
    patient_id: str
    status: EncounterStatus
    created_at: datetime
    updated_at: datetime
    notes: str | None
    soap_draft: dict | None = Field(None, description="SOAP JSON once orchestration completes")
    error_message: str | None = None


class SSEEvent(BaseModel):
    event: str
    data: dict
