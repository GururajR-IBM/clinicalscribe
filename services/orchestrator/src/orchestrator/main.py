"""FastAPI app entrypoint for the Orchestrator service.

Exposes one internal endpoint:
  POST /draft  — accepts transcript + metadata, returns SOAP JSON + codes + warnings.
               Called by the ingestion-worker after transcription.

Runs the 7-agent MAF supervisor topology. Bring-your-own LLM: set AOAI_ENDPOINT +
AOAI_KEY (any Azure OpenAI account); when unset, agents return safe stub data so
the pipeline still serves a 200 for local dev.
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI, HTTPException, status

from orchestrator import __version__
from orchestrator.config import settings
from orchestrator import supervisor
from orchestrator.schemas import (
    CodeItem,
    DraftRequest,
    DraftResponse,
    InteractionWarning,
    SOAPSection,
)

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level.upper())
    ),
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

app = FastAPI(
    title="ClinicalScribe Orchestrator",
    version=__version__,
    description="SOAP drafting agent runtime (Phase 2: 7-agent MAF supervisor).",
    docs_url="/docs" if settings.environment != "prod" else None,
    redoc_url="/redoc" if settings.environment != "prod" else None,
)


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.post(
    "/draft",
    response_model=DraftResponse,
    status_code=status.HTTP_200_OK,
    tags=["orchestration"],
    summary="Draft a SOAP note from a clinical transcript",
)
async def draft(body: DraftRequest) -> DraftResponse:
    """Run the 7-agent MAF supervisor pipeline and return SOAP JSON + codes + warnings.

    Called internally by the ingestion-worker. Not exposed publicly.
    Input size is bounded by FastAPI's body limit (default 1 MB).
    """
    log.info("draft_requested", encounter_id=str(body.encounter_id))
    try:
        state = await supervisor.run(
            encounter_id=body.encounter_id,
            patient_id=body.patient_id,
            transcript=body.transcript,
            notes=body.notes,
        )
    except Exception as exc:
        log.error("draft_error", encounter_id=str(body.encounter_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SOAP drafting failed. The encounter will be marked as failed.",
        )

    if state.soap_final is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supervisor completed but produced no SOAP output.",
        )

    soap_data = state.soap_final
    log.info(
        "draft_complete",
        encounter_id=str(body.encounter_id),
        in_tok=state.total_input_tokens,
        out_tok=state.total_output_tokens,
        codes=len(state.codes),
        warnings=len(state.interaction_warnings),
    )

    return DraftResponse(
        encounter_id=body.encounter_id,
        soap=SOAPSection(**soap_data),
        codes=[
            CodeItem(
                code=c.code,
                code_type=c.code_type,
                description=c.description,
                confidence=c.confidence,
                justification=c.justification,
            )
            for c in state.codes
        ],
        interaction_warnings=[
            InteractionWarning(
                drugs=w.drugs,
                severity=w.severity,
                description=w.description,
            )
            for w in state.interaction_warnings
        ],
        model_used=f"supervisor/{settings.aoai_review_model}",
        input_tokens=state.total_input_tokens,
        output_tokens=state.total_output_tokens,
    )


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "orchestrator", "version": __version__}
