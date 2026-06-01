"""Pydantic schemas for orchestrator API."""

from __future__ import annotations

import uuid
from typing import Any

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


class CodeItem(BaseModel):
    code: str
    code_type: str          # "icd10" | "cpt"
    description: str
    confidence: str         # "high" | "medium" | "low"
    justification: str


class InteractionWarning(BaseModel):
    drugs: list[str]
    severity: str
    description: str


class DraftResponse(BaseModel):
    encounter_id: uuid.UUID
    soap: SOAPSection
    codes: list[CodeItem] = Field(default_factory=list)
    interaction_warnings: list[InteractionWarning] = Field(default_factory=list)
    model_used: str
    input_tokens: int
    output_tokens: int
