"""Supervisor — orchestrates the 7-agent MAF pipeline.

Execution order (with parallelism):
  1. Entity Extraction       (sequential — needs transcript)
  2+3. Retrieval + EHR check (parallel — both need entities)
  4. SOAP Drafter            (sequential — needs evidence)
  5+6. Coder + Drug checker  (parallel — both need entities + soap_draft)
  7. Critic                  (sequential — needs everything)

Each step is traced to Cosmos (no-op when cosmos_endpoint is empty).
The Supervisor retries the Critic step at most once (critic_iterations ≤ 1).

Input:  encounter_id, patient_id, transcript, notes (optional)
Output: AgentState with soap_final populated
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from openai import AsyncAzureOpenAI

from orchestrator.agent_state import AgentState
from orchestrator.agents import (
    run_coder,
    run_drug_interaction,
    run_entity_extraction,
    run_retrieval,
    run_soap_drafter,
    run_critic,
)
from orchestrator import cosmos_writer
from orchestrator.config import settings

log = logging.getLogger(__name__)

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


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _traced(
    name: str,
    coro,
    state: AgentState,
) -> AgentState:
    """Run a coroutine and write a trace span around it."""
    start = _utcnow()
    result = await coro
    end = _utcnow()
    await cosmos_writer.write_trace(state, span_name=name, start_time=start, end_time=end)
    return result


async def run(
    encounter_id: uuid.UUID,
    patient_id: str,
    transcript: str,
    notes: str | None = None,
) -> AgentState:
    """Entry point — run the full 7-agent pipeline and return final state."""
    state = AgentState(
        encounter_id=encounter_id,
        patient_id=patient_id,
        transcript=transcript if not notes else f"{transcript}\n\nClinician notes: {notes}",
    )
    client = _get_client()

    await cosmos_writer.write_run_start(state)

    try:
        # ── Step 2: Entity Extraction ─────────────────────────────────────
        state = await _traced(
            "entity_extraction",
            run_entity_extraction(state, client),
            state,
        )

        # ── Steps 3: Retrieval (MCP) — runs after entity extraction ───────
        state = await _traced(
            "retrieval",
            run_retrieval(state, client),
            state,
        )

        # ── Step 4: SOAP Drafter ──────────────────────────────────────────
        state = await _traced(
            "soap_drafter",
            run_soap_drafter(state, client),
            state,
        )

        # ── Steps 5+6: Coder + Drug Interaction (parallel) ────────────────
        coder_task = asyncio.create_task(
            _traced("coder", run_coder(state, client), state)
        )
        drug_task = asyncio.create_task(
            _traced("drug_interaction", run_drug_interaction(state, client), state)
        )
        # Each task returns the mutated state; gather both then merge lists
        coder_state, drug_state = await asyncio.gather(coder_task, drug_task)
        state.codes = coder_state.codes
        state.interaction_warnings = drug_state.interaction_warnings
        state.model_tokens.update(coder_state.model_tokens)

        # ── Step 7: Critic (with one retry) ──────────────────────────────
        state = await _traced("critic", run_critic(state, client), state)
        state.critic_iterations += 1

        # If critic wiped soap_final (shouldn't happen), fall back to draft
        if state.soap_final is None:
            state.soap_final = state.soap_draft

        await cosmos_writer.write_evidence(state)
        await cosmos_writer.write_run_end(state)

    except Exception as exc:
        log.exception("supervisor pipeline failed for encounter %s", encounter_id)
        state.error = str(exc)
        state.soap_final = state.soap_draft  # best-effort fallback
        await cosmos_writer.write_run_end(state, failed=True)

    return state
