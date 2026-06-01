"""AgentState — single source of truth passed through all 7 agents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    source: str          # "ai_search" | "static_kb" | "ehr"
    document_id: str
    excerpt: str
    relevance_score: float
    cited_in: str        # "subjective" | "objective" | "assessment" | "plan"


@dataclass
class CodeItem:
    code: str            # e.g. "J18.9" or "99213"
    code_type: str       # "icd10" | "cpt"
    description: str
    confidence: str      # "high" | "medium" | "low"
    justification: str


@dataclass
class InteractionWarning:
    drugs: list[str]
    severity: str        # from openFDA or static: "major" | "moderate" | "minor"
    description: str


@dataclass
class AgentState:
    # Identity
    encounter_id: uuid.UUID
    patient_id: str

    # Step 1 — Transcription Agent
    transcript: str = ""

    # Step 2 — Entity Extraction Agent
    entities: dict[str, list[str]] = field(default_factory=dict)
    # keys: "diagnoses", "medications", "allergies", "vitals", "procedures"

    # Step 3 — Retrieval Agent
    evidence: list[EvidenceItem] = field(default_factory=list)

    # Step 4 — SOAP Drafter Agent
    soap_draft: dict[str, str] | None = None
    # keys: "subjective", "objective", "assessment", "plan"

    # Step 5 — Coder Agent
    codes: list[CodeItem] = field(default_factory=list)

    # Step 6 — Drug Interaction Agent
    interaction_warnings: list[InteractionWarning] = field(default_factory=list)

    # Step 7 — Critic Agent
    soap_final: dict[str, str] | None = None
    critic_iterations: int = 0

    # Token accounting (keyed by model name)
    model_tokens: dict[str, dict[str, int]] = field(default_factory=dict)
    # e.g. {"gpt-4o-mini": {"input": 1200, "output": 430}, "gpt-4o": {...}}

    # Run metadata
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    error: str | None = None

    def add_tokens(self, model: str, input_tokens: int, output_tokens: int) -> None:
        if model not in self.model_tokens:
            self.model_tokens[model] = {"input": 0, "output": 0}
        self.model_tokens[model]["input"] += input_tokens
        self.model_tokens[model]["output"] += output_tokens

    @property
    def total_input_tokens(self) -> int:
        return sum(v["input"] for v in self.model_tokens.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(v["output"] for v in self.model_tokens.values())
