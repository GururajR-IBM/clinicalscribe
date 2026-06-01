"""Phase 2 MAF agents — each agent is a pure async function.

All agents accept an AgentState, mutate it, and return it.
Agents never directly call Azure services — they call MCP tool stubs or
the shared AsyncAzureOpenAI client passed in by the Supervisor.

OWASP A03: transcript/SOAP content is always in user messages.
System prompts are static module-level constants — no user data interpolation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from openai import AsyncAzureOpenAI

from orchestrator.agent_state import AgentState, CodeItem, EvidenceItem, InteractionWarning
from orchestrator.config import settings

log = logging.getLogger(__name__)

# ── Shared helpers ─────────────────────────────────────────────────────────


def _json_or_empty(text: str) -> dict:
    """Strip markdown fences and parse JSON; return {} on failure."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


async def _mcp_call(base_url: str, tool: str, arguments: dict) -> dict:
    """HTTP call to an MCP server tool endpoint.

    MCP JSON-RPC wire format: POST /  body = {jsonrpc, method, params, id}.
    Falls back to {} on any error so agents degrade gracefully.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                base_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool, "arguments": arguments},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "{}")
                return json.loads(text) if text.strip().startswith("{") else {}
    except Exception as exc:  # noqa: BLE001
        log.debug("mcp_call %s/%s failed: %s", base_url, tool, exc)
    return {}


# ── Agent 2 — Entity Extraction ───────────────────────────────────────────

_ENTITY_SYSTEM = (
    "You are a clinical NLP specialist. Extract structured entities from a medical encounter "
    "transcript. Return ONLY a JSON object with keys: "
    '"diagnoses" (list[str]), "medications" (list[str]), "allergies" (list[str]), '
    '"vitals" (list[str]), "procedures" (list[str]). '
    "Each value is a list of plain strings. Omit empty lists. "
    "Do not fabricate entities not present in the transcript."
)


async def run_entity_extraction(state: AgentState, client: AsyncAzureOpenAI) -> AgentState:
    """Extract diagnoses, medications, allergies, vitals, procedures from transcript."""
    if not settings.aoai_key:
        log.info("entity_extraction: no AOAI key — using stub entities")
        state.entities = {"diagnoses": ["unspecified condition"], "medications": [], "allergies": [], "vitals": [], "procedures": []}
        return state

    try:
        response = await client.chat.completions.create(
            model=settings.aoai_draft_model,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _ENTITY_SYSTEM},
                {"role": "user", "content": state.transcript[:50_000]},
            ],
        )
        usage = response.usage
        state.add_tokens(settings.aoai_draft_model, usage.prompt_tokens, usage.completion_tokens)
        entities = _json_or_empty(response.choices[0].message.content or "")
        state.entities = {k: v for k, v in entities.items() if isinstance(v, list)}
    except Exception as exc:
        log.warning("entity_extraction failed: %s", exc)
        state.entities = {}

    # Enrich with EHR patient history via MCP
    if state.patient_id:
        ehr = await _mcp_call(
            settings.mcp_ehr_url,
            "get_patient_history",
            {"patient_id": state.patient_id},
        )
        if ehr.get("conditions"):
            existing = state.entities.setdefault("diagnoses", [])
            for c in ehr["conditions"]:
                label = f"{c.get('name', '')} (existing)"
                if label not in existing:
                    existing.append(label)
        if ehr.get("medications"):
            existing = state.entities.setdefault("medications", [])
            for m in ehr["medications"]:
                label = f"{m.get('name', '')} (existing)"
                if label not in existing:
                    existing.append(label)

    return state


# ── Agent 3 — Retrieval ────────────────────────────────────────────────────

async def run_retrieval(state: AgentState, _client: AsyncAzureOpenAI) -> AgentState:
    """Retrieve clinical guideline evidence for the top entities."""
    diagnoses = state.entities.get("diagnoses", [])[:5]
    if not diagnoses:
        return state

    seen: set[str] = set()
    for dx in diagnoses:
        result = await _mcp_call(
            settings.mcp_medical_kb_url,
            "lookup_term",
            {"term": dx[:200]},
        )
        doc_id = result.get("term", dx)
        if doc_id in seen:
            continue
        seen.add(doc_id)
        definition = result.get("definition", "")
        icd = result.get("icd10", "")
        if definition:
            state.evidence.append(EvidenceItem(
                source=result.get("source", "static_kb"),
                document_id=doc_id,
                excerpt=f"{definition} (ICD-10: {icd})" if icd else definition,
                relevance_score=result.get("score", 0.9),
                cited_in="assessment",
            ))

    return state


# ── Agent 4 — SOAP Drafter ─────────────────────────────────────────────────

_DRAFTER_SYSTEM = (
    "You are a clinical documentation specialist. "
    "Compose a structured SOAP note from the provided transcript, extracted entities, "
    "and retrieved evidence. Return ONLY a JSON object with keys: "
    '"subjective", "objective", "assessment", "plan". '
    "Each value is a plain string. "
    "Cite evidence where appropriate (e.g., 'per clinical guidelines'). "
    "Do not fabricate findings. If a section has no data, write "
    '"Not documented in this encounter."'
)


async def run_soap_drafter(state: AgentState, client: AsyncAzureOpenAI) -> AgentState:
    """Draft the SOAP note from entities + evidence + transcript."""
    if not settings.aoai_key:
        log.info("soap_drafter: no AOAI key — using stub SOAP")
        state.soap_draft = {
            "subjective": "Stub: patient reported symptoms not available in local dev.",
            "objective": "Not documented in this encounter.",
            "assessment": "Not documented in this encounter.",
            "plan": "Not documented in this encounter.",
        }
        return state

    evidence_text = "\n".join(f"- {e.excerpt}" for e in state.evidence[:10]) or "None retrieved."
    entities_text = json.dumps(state.entities, indent=2)

    try:
        response = await client.chat.completions.create(
            model=settings.aoai_draft_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _DRAFTER_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"TRANSCRIPT:\n{state.transcript[:40_000]}\n\n"
                        f"EXTRACTED ENTITIES:\n{entities_text}\n\n"
                        f"RETRIEVED EVIDENCE:\n{evidence_text}"
                    ),
                },
            ],
        )
        usage = response.usage
        state.add_tokens(settings.aoai_draft_model, usage.prompt_tokens, usage.completion_tokens)
        draft = _json_or_empty(response.choices[0].message.content or "")
        for key in ("subjective", "objective", "assessment", "plan"):
            draft.setdefault(key, "Not documented in this encounter.")
        state.soap_draft = draft
    except Exception as exc:
        log.warning("soap_drafter failed: %s", exc)
        state.soap_draft = {k: "Not documented in this encounter." for k in ("subjective", "objective", "assessment", "plan")}

    return state


# ── Agent 5 — Coder ────────────────────────────────────────────────────────

async def run_coder(state: AgentState, _client: AsyncAzureOpenAI) -> AgentState:
    """Suggest ICD-10 and CPT codes from the SOAP assessment/plan."""
    diagnoses = state.entities.get("diagnoses", [])[:5]
    procedures = state.entities.get("procedures", [])[:5]

    for dx in diagnoses:
        result = await _mcp_call(settings.mcp_coding_url, "search_icd10", {"query": dx[:200]})
        code = result.get("code")
        if code:
            just = await _mcp_call(
                settings.mcp_coding_url,
                "justify_code",
                {"code": code, "transcript_snippet": (state.soap_draft or {}).get("assessment", "")[:500]},
            )
            state.codes.append(CodeItem(
                code=code,
                code_type="icd10",
                description=result.get("description", dx),
                confidence=just.get("confidence", "low"),
                justification=just.get("rationale", ""),
            ))

    for proc in procedures:
        result = await _mcp_call(settings.mcp_coding_url, "search_cpt", {"query": proc[:200]})
        code = result.get("code")
        if code:
            state.codes.append(CodeItem(
                code=code,
                code_type="cpt",
                description=result.get("description", proc),
                confidence="medium",
                justification="Procedure mentioned in transcript.",
            ))

    return state


# ── Agent 6 — Drug Interaction ─────────────────────────────────────────────

async def run_drug_interaction(state: AgentState, _client: AsyncAzureOpenAI) -> AgentState:
    """Check all medications for drug-drug interactions."""
    all_meds: list[str] = []
    for m in state.entities.get("medications", []):
        # Strip "(existing)" suffix added by entity extraction
        all_meds.append(m.replace(" (existing)", "").strip())

    if len(all_meds) < 2:
        return state

    result = await _mcp_call(settings.mcp_drug_url, "check_combo", {"drugs": all_meds[:20]})
    for interaction in result.get("interactions", []):
        state.interaction_warnings.append(InteractionWarning(
            drugs=interaction.get("drugs", []),
            severity=interaction.get("severity", "unknown"),
            description=interaction.get("description", ""),
        ))

    return state


# ── Agent 7 — Critic ───────────────────────────────────────────────────────

_CRITIC_SYSTEM = (
    "You are a senior physician reviewing a SOAP note for completeness and accuracy. "
    "You will receive the original transcript, extracted entities, retrieved evidence, "
    "the SOAP draft, suggested codes, and any drug interaction warnings. "
    "\n\nCheck:\n"
    "a. Every claim in the SOAP is supported by the transcript or evidence.\n"
    "b. ICD-10/CPT codes are consistent with the assessment/plan.\n"
    "c. Drug interaction warnings (if any) are mentioned in the plan.\n"
    "d. Each SOAP section is clinically appropriate in length and language.\n"
    "\nIf the draft passes all checks, return it unchanged. "
    "If corrections are needed, return a corrected version. "
    "Return ONLY a JSON object with keys: subjective, objective, assessment, plan. "
    "No markdown, no explanations."
)


async def run_critic(state: AgentState, client: AsyncAzureOpenAI) -> AgentState:
    """Validate and optionally rewrite the SOAP draft; populate soap_final."""
    if not settings.aoai_key or state.soap_draft is None:
        state.soap_final = state.soap_draft
        return state

    warning_text = (
        "\n".join(
            f"- {w.severity.upper()}: {', '.join(w.drugs)} — {w.description}"
            for w in state.interaction_warnings
        )
        or "None."
    )
    codes_text = (
        "\n".join(f"- {c.code} ({c.code_type}): {c.description} [{c.confidence}]" for c in state.codes)
        or "None suggested."
    )

    try:
        response = await client.chat.completions.create(
            model=settings.aoai_review_model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _CRITIC_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"TRANSCRIPT:\n{state.transcript[:20_000]}\n\n"
                        f"SOAP DRAFT:\n{json.dumps(state.soap_draft, indent=2)}\n\n"
                        f"SUGGESTED CODES:\n{codes_text}\n\n"
                        f"DRUG INTERACTION WARNINGS:\n{warning_text}"
                    ),
                },
            ],
        )
        usage = response.usage
        state.add_tokens(settings.aoai_review_model, usage.prompt_tokens, usage.completion_tokens)
        reviewed = _json_or_empty(response.choices[0].message.content or "")
        for key in ("subjective", "objective", "assessment", "plan"):
            reviewed.setdefault(key, state.soap_draft.get(key, "Not documented."))
        state.soap_final = reviewed
    except Exception as exc:
        log.warning("critic failed: %s", exc)
        state.soap_final = state.soap_draft

    return state
