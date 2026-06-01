"""Smoke test for eval-runner stub."""

from eval_runner.main import main


def test_main_returns_zero() -> None:
    assert main() == 0
