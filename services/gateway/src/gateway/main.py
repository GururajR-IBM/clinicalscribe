"""FastAPI app entrypoint for the Gateway service."""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway import __version__
from gateway.config import settings
from gateway.routers.encounters import router as encounters_router

logging.basicConfig(level=settings.log_level.upper())
log = structlog.get_logger()

app = FastAPI(
    title="ClinicalScribe Gateway",
    version=__version__,
    description="Public REST + SSE API for ClinicalScribe.",
    docs_url="/docs" if settings.environment != "prod" else None,
    redoc_url="/redoc" if settings.environment != "prod" else None,
)

# CORS — tighten origins in prod via environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "local" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(encounters_router)


# ── Health probes ──────────────────────────────────────────────────────────
@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readyz() -> dict[str, str]:
    """Readiness probe. Checks downstream deps from Phase 1.10 onward."""
    return {"status": "ready"}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "gateway", "version": __version__}

