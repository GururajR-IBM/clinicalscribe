"""Tests for the orchestrator service."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from orchestrator.main import app

client = TestClient(app)


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz() -> None:
    resp = client.get("/readyz")
    assert resp.status_code == 200


def test_draft_returns_soap_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /draft returns a valid SOAP response using the local stub (no AOAI key)."""
    # Ensure no key is set so the stub path is exercised
    monkeypatch.setenv("AOAI_KEY", "")

    resp = client.post(
        "/draft",
        json={
            "encounter_id": str(uuid.uuid4()),
            "patient_id": "patient-001",
            "transcript": "Patient presents with fever and cough.",
            "notes": None,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "soap" in body
    soap = body["soap"]
    assert all(k in soap for k in ("subjective", "objective", "assessment", "plan"))
    assert len(soap["subjective"]) > 5


def test_draft_rejects_empty_transcript() -> None:
    resp = client.post(
        "/draft",
        json={
            "encounter_id": str(uuid.uuid4()),
            "patient_id": "patient-001",
            "transcript": "",
        },
    )
    assert resp.status_code == 422  # Pydantic min_length=1 validation


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "orchestrator"
