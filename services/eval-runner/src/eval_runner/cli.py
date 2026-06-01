"""Typer CLI entry point for eval-runner."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer

from eval_runner.main import run_eval

app = typer.Typer(name="eval-runner", add_completion=False)


@app.command()
def evaluate(
    dataset: Path = typer.Option(None, "--dataset", "-d", help="Path to golden_dataset.json"),
    ci: bool = typer.Option(False, "--ci", help="Exit 1 if pass rate < 80%"),
) -> None:
    """Run the evaluation suite against the orchestrator."""
    exit_code = asyncio.run(run_eval(dataset_path=dataset, ci_mode=ci) if dataset else run_eval(ci_mode=ci))
    sys.exit(exit_code)


if __name__ == "__main__":
    app()
