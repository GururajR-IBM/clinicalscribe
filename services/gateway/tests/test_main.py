"""Smoke tests for the gateway service."""

from fastapi.testclient import TestClient

from gateway.main import app

client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz() -> None:
    response = client.get("/readyz")
    assert response.status_code == 200


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "gateway"
