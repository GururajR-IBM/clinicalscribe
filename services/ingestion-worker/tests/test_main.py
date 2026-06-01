"""Smoke test for ingestion-worker stub."""

from ingestion_worker.main import main


def test_main_returns_zero() -> None:
    assert main() == 0
