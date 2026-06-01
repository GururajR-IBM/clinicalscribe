"""FastAPI app entrypoint for the Orchestrator service."""

from __future__ import annotations

from fastapi import FastAPI

from orchestrator import __version__

app = FastAPI(
    title="ClinicalScribe Orchestrator",
    version=__version__,
    description="MAF agent runtime. Supervisor + specialist agents.",
)


@app.get("/healthz", tags=["health"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "orchestrator", "version": __version__}
