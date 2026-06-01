"""Eval rubric — dimension definitions and LLM-judge scoring.

Each SOAP note is scored on 5 dimensions (0–10 each):
  1. medical_correctness   — factual accuracy vs. transcript
  2. citation_faithfulness — every SOAP claim is grounded in evidence or transcript
  3. coding_accuracy       — ICD-10/CPT codes match assessment/plan
  4. completeness          — all 4 SOAP sections non-empty and non-generic
  5. drug_safety           — all interaction warnings acknowledged in the plan

Total score = weighted average (weights below).
Pass threshold: total >= 7.0 AND no dimension < 4.0.

NOTE (Phase 5 reminder): regenerate rubric prompts and ADR 0003 Consequences section
using Claude Opus 4.7 once eval results from the golden dataset are available.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from openai import AsyncAzureOpenAI

from eval_runner.config import settings

log = logging.getLogger(__name__)

DIMENSION_WEIGHTS = {
    "medical_correctness": 0.30,
    "citation_faithfulness": 0.25,
    "coding_accuracy": 0.20,
    "completeness": 0.15,
    "drug_safety": 0.10,
}

# ── Dimension scoring prompts ──────────────────────────────────────────────
# System prompt: static (OWASP A03 — no user data in system)

_JUDGE_SYSTEM = (
    "You are an expert clinical quality auditor with 20 years of experience reviewing "
    "AI-generated medical documentation. You evaluate SOAP notes against a provided "
    "reference transcript and return structured JSON scores. "
    "Be strict: do not award more than 6/10 if there are any unsupported claims. "
    "Return ONLY a JSON object with integer scores 0-10 and a brief rationale string per dimension."
)

_JUDGE_SCHEMA = {
    "medical_correctness": {"score": 0, "rationale": ""},
    "citation_faithfulness": {"score": 0, "rationale": ""},
    "coding_accuracy": {"score": 0, "rationale": ""},
    "completeness": {"score": 0, "rationale": ""},
    "drug_safety": {"score": 0, "rationale": ""},
}


@dataclass
class DimensionScore:
    score: float        # 0–10
    rationale: str


@dataclass
class EvalResult:
    case_id: str
    total_score: float
    passed: bool
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    raw_judge_output: str = ""
    error: str | None = None


_client: AsyncAzureOpenAI | None = None


def _get_client() -> AsyncAzureOpenAI:
    global _client
    if _client is None:
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.aoai_endpoint,
            api_key=settings.aoai_key or "stub",
            api_version=settings.aoai_api_version,
        )
    return _client


async def score_soap(
    *,
    case_id: str,
    transcript: str,
    soap: dict[str, str],
    codes: list[dict],
    interaction_warnings: list[dict],
    reference_codes: list[str] | None = None,
) -> EvalResult:
    """Run the LLM-judge over one SOAP note and return an EvalResult.

    Falls back to stub scores when AOAI key is absent (local/lab dev).
    """
    if not settings.aoai_key:
        log.info("eval_stub: no AOAI key — returning stub scores for %s", case_id)
        dims = {k: DimensionScore(score=7.0, rationale="stub") for k in DIMENSION_WEIGHTS}
        total = 7.0
        return EvalResult(case_id=case_id, total_score=total, passed=True, dimensions=dims)

    ref_codes_text = ", ".join(reference_codes) if reference_codes else "None provided."
    warnings_text = (
        "\n".join(f"- {w.get('severity','?').upper()}: {', '.join(w.get('drugs', []))} — {w.get('description','')}" for w in interaction_warnings)
        or "None."
    )
    codes_text = (
        "\n".join(f"- {c.get('code')} ({c.get('code_type')}): {c.get('description')} [{c.get('confidence')}]" for c in codes)
        or "None suggested."
    )

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.aoai_judge_model,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"TRANSCRIPT (source of truth):\n{transcript[:15_000]}\n\n"
                        f"SOAP NOTE:\n{json.dumps(soap, indent=2)}\n\n"
                        f"SUGGESTED CODES:\n{codes_text}\n\n"
                        f"REFERENCE CODES (ground truth):\n{ref_codes_text}\n\n"
                        f"DRUG INTERACTION WARNINGS:\n{warnings_text}\n\n"
                        "Score each dimension 0-10. Return JSON with keys: "
                        "medical_correctness, citation_faithfulness, coding_accuracy, "
                        "completeness, drug_safety. Each key maps to {score: int, rationale: str}."
                    ),
                },
            ],
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
    except Exception as exc:
        log.warning("judge_call_failed: %s", exc)
        return EvalResult(case_id=case_id, total_score=0.0, passed=False, error=str(exc))

    dims: dict[str, DimensionScore] = {}
    for dim, weight in DIMENSION_WEIGHTS.items():
        entry = data.get(dim, {})
        score = float(entry.get("score", 0))
        dims[dim] = DimensionScore(score=score, rationale=entry.get("rationale", ""))

    total = sum(dims[d].score * w for d, w in DIMENSION_WEIGHTS.items())
    passed = total >= 7.0 and all(dims[d].score >= 4.0 for d in DIMENSION_WEIGHTS)

    return EvalResult(
        case_id=case_id,
        total_score=round(total, 2),
        passed=passed,
        dimensions=dims,
        raw_judge_output=raw,
    )
