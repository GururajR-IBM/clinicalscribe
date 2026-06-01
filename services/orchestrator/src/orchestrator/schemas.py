"""Pydantic schemas for orchestrator API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class DraftRequest(BaseModel):
    encounter_id: uuid.UUID
    patient_id: str
    transcript: str = Field(..., min_length=1, max_length=100_000)
    notes: str | None = None


class SOAPSection(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


class DraftResponse(BaseModel):
    encounter_id: uuid.UUID
    soap: SOAPSection
    model_used: str
    input_tokens: int
    output_tokens: int
