"""Encounter — the unit of work for ClinicalScribe."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EncounterStatus(StrEnum):
    """Lifecycle states for an encounter."""

    DRAFT = "draft"
    INGESTING = "ingesting"
    AGENT_RUNNING = "agent_running"
    AWAITING_REVIEW = "awaiting_review"
    SIGNED = "signed"
    ARCHIVED = "archived"
    FAILED = "failed"


class Encounter(BaseModel):
    """A single patient visit being documented."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    patient_id: UUID
    clinician_id: UUID
    status: EncounterStatus = EncounterStatus.DRAFT
    created_at: datetime
    updated_at: datetime
    title: str = Field(min_length=1, max_length=200)
