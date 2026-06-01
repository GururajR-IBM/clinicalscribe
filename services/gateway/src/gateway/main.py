"""FastAPI app entrypoint for the Gateway service."""

from __future__ import annotations

from fastapi import FastAPI

from gateway import __version__

app = FastAPI(
    title="ClinicalScribe Gateway",
    version=__version__,
    description="Public REST + SSE API for ClinicalScribe.",
)


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readyz() -> dict[str, str]:
    """Readiness probe. Will check downstream deps in Phase 1."""
    return {"status": "ready"}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "gateway", "version": __version__}
