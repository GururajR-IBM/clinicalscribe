"""Typer CLI entry point for eval-runner."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer

from eval_runner.main import _DEFAULT_DATASET, run_eval

app = typer.Typer(name="eval-runner", add_completion=False)


@app.command()
def evaluate(
    dataset: Optional[Path] = typer.Option(
        None, "--dataset", "-d", help="Path to golden_dataset.json"
    ),
    ci: bool = typer.Option(False, "--ci", help="Exit 1 if pass rate < 80%"),
) -> None:
    """Run the evaluation suite against the orchestrator."""
    path = dataset if dataset is not None else _DEFAULT_DATASET
    exit_code = asyncio.run(run_eval(dataset_path=path, ci_mode=ci))
    sys.exit(exit_code)


if __name__ == "__main__":
    app()
