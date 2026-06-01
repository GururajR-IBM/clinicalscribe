"""Eval runner — batch evaluation of orchestrator SOAP output against a golden dataset.

Phase 5 tasks:
  5.1  Load golden dataset (data/golden_dataset.json)
  5.2  For each case, call the orchestrator /draft endpoint
  5.3  Score output with LLM-judge rubric (rubric.py)
  5.4  Report results; fail CI if pass rate < 80 %

NOTE: Use Opus 4.7 for reviewing ADR 0003 Consequences and regenerating rubric prompts
      once Phase 5 eval results are available.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx
import structlog

from eval_runner import __version__
from eval_runner.config import settings
from eval_runner.rubric import EvalResult, score_soap

log = structlog.get_logger()

# Path relative to the package root; keep data/ outside src/
_DEFAULT_DATASET = Path(__file__).parent.parent.parent / "data" / "golden_dataset.json"


def load_golden_dataset(path: Path = _DEFAULT_DATASET) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


async def evaluate_case(client: httpx.AsyncClient, case: dict) -> EvalResult:
    case_id: str = case["id"]
    log.info("evaluating", case_id=case_id)

    try:
        resp = await client.post(
            "/draft",
            json={
                "encounter_id": case_id,
                "patient_id": "eval-patient",
                "transcript": case["transcript"],
                "notes": None,
            },
            timeout=settings.orchestrator_timeout,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as exc:
        log.error("orchestrator_error", case_id=case_id, error=str(exc))
        return EvalResult(case_id=case_id, total_score=0.0, passed=False, error=str(exc))

    soap = result.get("soap") or {}
    codes = result.get("codes", [])
    warnings = result.get("interaction_warnings", [])

    return await score_soap(
        case_id=case_id,
        transcript=case["transcript"],
        soap=soap,
        codes=codes,
        interaction_warnings=warnings,
        reference_codes=case.get("expected_codes"),
    )


async def run_eval(dataset_path: Path = _DEFAULT_DATASET, ci_mode: bool = False) -> int:
    """Run evaluation suite. Returns exit code 0 (pass) or 1 (fail)."""
    log.info("eval_start", version=__version__, dataset=str(dataset_path))
    cases = load_golden_dataset(dataset_path)

    results: list[EvalResult] = []
    async with httpx.AsyncClient(base_url=settings.orchestrator_url) as client:
        for case in cases:
            result = await evaluate_case(client, case)
            results.append(result)

    # ── Summary ───────────────────────────────────────────────────────────
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    pass_rate = len(passed) / len(results) * 100 if results else 0.0

    print("\n" + "=" * 60)
    print(f"EVAL SUMMARY  — {__version__}")
    print(f"Total: {len(results)}  Passed: {len(passed)}  Failed: {len(failed)}")
    print(f"Pass rate: {pass_rate:.1f}%  (threshold: 80%)")
    print("-" * 60)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        error_info = f"  error={r.error}" if r.error else ""
        print(f"  [{status}] {r.case_id}  total={r.total_score:.2f}{error_info}")
        for dim, ds in (r.dimensions or {}).items():
            print(f"        {dim}: {ds.score:.1f}  — {ds.rationale[:80]}")
    print("=" * 60 + "\n")

    # ── Persist results to eval_results/ ──────────────────────────────────
    out_dir = Path(settings.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "latest.json"
    out_file.write_text(
        json.dumps(
            {
                "version": __version__,
                "pass_rate": pass_rate,
                "results": [
                    {
                        "case_id": r.case_id,
                        "total_score": r.total_score,
                        "passed": r.passed,
                        "error": r.error,
                        "dimensions": {
                            k: {"score": v.score, "rationale": v.rationale}
                            for k, v in (r.dimensions or {}).items()
                        },
                    }
                    for r in results
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info("results_written", path=str(out_file))

    if ci_mode and pass_rate < 80.0:
        log.error("ci_threshold_not_met", pass_rate=pass_rate)
        return 1
    return 0


def main() -> int:
    return asyncio.run(run_eval(ci_mode="--ci" in sys.argv))


if __name__ == "__main__":
    sys.exit(main())

