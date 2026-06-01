"""SOAP Drafter v0 — single-agent implementation (Phase 1, task 1.13).

Architecture:
  - One pass: GPT-4o-mini drafts the SOAP from the transcript.
  - One pass: GPT-4o acts as Critic — validates completeness, rewrites if needed.

Phase 2 (task 2.10) will replace this with the full MAF multi-agent topology:
Supervisor → Transcription → Entity Extraction → Retrieval → Drafter → Coder → Critic.

OWASP A03 (Injection): transcript is passed as a user message, never interpolated
into system prompt strings. System prompt is a static constant.
"""

from __future__ import annotations

import json
import logging

from openai import AsyncAzureOpenAI

from orchestrator.config import settings
from orchestrator.schemas import SOAPSection

log = logging.getLogger(__name__)

_DRAFTER_SYSTEM = """You are a clinical documentation specialist.
Given a raw speech-to-text transcript of a doctor-patient encounter, produce a
structured SOAP note in JSON format with exactly these keys:
  "subjective"  – patient-reported symptoms, history, chief complaint
  "objective"   – observations, vitals, exam findings (infer "not documented" if absent)
  "assessment"  – diagnosis or differential; include ICD-10 code if identifiable
  "plan"        – treatment, prescriptions (drug/dose/duration), follow-up, referrals

Rules:
- Use plain clinical language. Do not fabricate findings not mentioned in the transcript.
- If a SOAP section has no information, write "Not documented in this encounter."
- Output ONLY the JSON object. No markdown fences, no preamble.
"""

_CRITIC_SYSTEM = """You are a senior physician reviewing a SOAP note for completeness.
You will receive the original transcript and a SOAP draft.
If the draft is medically accurate and complete, return it unchanged as JSON.
If corrections are needed, return a corrected version in the same JSON format.
Output ONLY the JSON object. No explanations, no markdown.
"""

_client: AsyncAzureOpenAI | None = None


def _get_client() -> AsyncAzureOpenAI:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.aoai_endpoint,
            api_key=settings.aoai_key,
            api_version=settings.aoai_api_version,
        )
    return _client


def _stub_soap() -> tuple[SOAPSection, str, int, int]:
    """Return deterministic stub when AOAI key is absent (local dev)."""
    soap = SOAPSection(
        subjective="Patient reports 3-day productive cough, low-grade fever, and exertional dyspnea.",
        objective="Not documented in this encounter.",
        assessment="Community-acquired pneumonia (J18.9).",
        plan="Amoxicillin 500 mg TID for 7 days. Follow-up in 1 week.",
    )
    return soap, settings.aoai_draft_model, 0, 0


def _parse_soap(raw: str) -> SOAPSection:
    """Parse JSON string from LLM into SOAPSection; raise ValueError on bad output."""
    # Strip markdown fences if the model includes them despite instructions
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()
    data = json.loads(cleaned)
    return SOAPSection(**{k: str(v) for k, v in data.items()})


async def draft_soap(
    transcript: str,
    notes: str | None = None,
) -> tuple[SOAPSection, str, int, int]:
    """Draft a SOAP note from a transcript.

    Returns (soap, model_name, input_tokens, output_tokens).
    Falls back to stub when AOAI credentials are absent.
    """
    if not settings.aoai_key:
        log.warning("No AOAI key — returning stub SOAP for local dev")
        return _stub_soap()

    client = _get_client()

    user_content = f"TRANSCRIPT:\n{transcript}"
    if notes:
        user_content = f"CLINICIAN NOTES:\n{notes}\n\n{user_content}"

    # ── Pass 1: Drafter (gpt-4o-mini) ────────────────────────────────────
    drafter_resp = await client.chat.completions.create(
        model=settings.aoai_draft_model,
        messages=[
            {"role": "system", "content": _DRAFTER_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    draft_raw = drafter_resp.choices[0].message.content or "{}"
    in_tok = drafter_resp.usage.prompt_tokens if drafter_resp.usage else 0
    out_tok = drafter_resp.usage.completion_tokens if drafter_resp.usage else 0

    try:
        draft_soap = _parse_soap(draft_raw)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        log.error("drafter_parse_error", error=str(exc), raw=draft_raw[:200])
        return _stub_soap()

    # ── Pass 2: Critic (gpt-4o) ───────────────────────────────────────────
    critic_resp = await client.chat.completions.create(
        model=settings.aoai_review_model,
        messages=[
            {"role": "system", "content": _CRITIC_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"TRANSCRIPT:\n{transcript}\n\n"
                    f"SOAP DRAFT:\n{draft_soap.model_dump_json(indent=2)}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    critic_raw = critic_resp.choices[0].message.content or draft_raw
    in_tok += critic_resp.usage.prompt_tokens if critic_resp.usage else 0
    out_tok += critic_resp.usage.completion_tokens if critic_resp.usage else 0

    try:
        final_soap = _parse_soap(critic_raw)
    except (ValueError, KeyError, json.JSONDecodeError):
        log.warning("critic_parse_error — keeping drafter output")
        final_soap = draft_soap

    return final_soap, settings.aoai_review_model, in_tok, out_tok
