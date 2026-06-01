"""FastAPI app entrypoint for the Orchestrator service — Phase 1 (task 1.13).

Exposes one internal endpoint:
  POST /draft  — accepts transcript + metadata, returns SOAP JSON.
               Called by the ingestion-worker after transcription.

Phase 2 replaces the single drafter→critic pair with the full MAF topology.
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI, HTTPException, status

from orchestrator import __version__
from orchestrator.config import settings
from orchestrator.drafter import draft_soap
from orchestrator.schemas import DraftRequest, DraftResponse

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
    description="SOAP drafting agent runtime (Phase 1: single-agent drafter + critic).",
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
    """Run the SOAP Drafter v0 pipeline and return structured SOAP JSON.

    Called internally by the ingestion-worker. Not exposed publicly.
    Input size is bounded by FastAPI's body limit (default 1 MB).
    """
    log.info("draft_requested", encounter_id=str(body.encounter_id))
    try:
        soap, model_used, in_tok, out_tok = await draft_soap(
            transcript=body.transcript,
            notes=body.notes,
        )
    except Exception as exc:
        log.error("draft_error", encounter_id=str(body.encounter_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SOAP drafting failed. The encounter will be marked as failed.",
        )

    log.info(
        "draft_complete",
        encounter_id=str(body.encounter_id),
        model=model_used,
        in_tok=in_tok,
        out_tok=out_tok,
    )

    return DraftResponse(
        encounter_id=body.encounter_id,
        soap=soap,
        model_used=model_used,
        input_tokens=in_tok,
        output_tokens=out_tok,
    )


@app.get("/readyz", tags=["health"])
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "orchestrator", "version": __version__}
