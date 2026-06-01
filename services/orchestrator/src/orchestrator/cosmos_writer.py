"""Cosmos DB writer — persists AgentState snapshots to agent_runs + evidence + traces.

Gracefully no-ops when cosmos_endpoint is empty (local dev, lab sub).
Uses the Azure Cosmos DB Python SDK (azure-cosmos).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from orchestrator.agent_state import AgentState
from orchestrator.config import settings

log = logging.getLogger(__name__)

_client = None
_db = None


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_container(name: str):
    """Return a Cosmos container client, initialising lazily."""
    global _client, _db
    if not settings.cosmos_endpoint:
        return None
    try:
        from azure.cosmos.aio import CosmosClient  # type: ignore
        if _client is None:
            _client = CosmosClient(settings.cosmos_endpoint, settings.cosmos_key)
        if _db is None:
            _db = _client.get_database_client(settings.cosmos_database)
        return _db.get_container_client(name)
    except Exception:  # noqa: BLE001
        return None


async def write_run_start(state: AgentState) -> None:
    """Upsert an agent_run document when a run begins."""
    container = _get_container("agent_runs")
    if container is None:
        return
    try:
        doc = {
            "id": str(state.run_id),
            "encounter_id": str(state.encounter_id),
            "patient_id": state.patient_id,
            "started_at": _utcnow(),
            "completed_at": None,
            "status": "running",
            "error": None,
        }
        await container.upsert_item(doc)
    except Exception as exc:  # noqa: BLE001
        log.warning("cosmos write_run_start failed: %s", exc)


async def write_run_end(state: AgentState, *, failed: bool = False) -> None:
    """Update the agent_run document on completion or failure."""
    container = _get_container("agent_runs")
    if container is None:
        return
    try:
        doc = {
            "id": str(state.run_id),
            "encounter_id": str(state.encounter_id),
            "patient_id": state.patient_id,
            "completed_at": _utcnow(),
            "status": "failed" if failed else "complete",
            "error": state.error,
            "model_tokens": state.model_tokens,
            "critic_iterations": state.critic_iterations,
            "state_snapshot": {
                "entities": state.entities,
                "codes": [c.__dict__ for c in state.codes],
                "interaction_warnings": [w.__dict__ for w in state.interaction_warnings],
            },
        }
        await container.upsert_item(doc)
    except Exception as exc:  # noqa: BLE001
        log.warning("cosmos write_run_end failed: %s", exc)


async def write_evidence(state: AgentState) -> None:
    """Bulk-upsert all evidence items for this run."""
    container = _get_container("evidence")
    if container is None or not state.evidence:
        return
    try:
        import uuid as _uuid

        async def _upsert(item):
            await container.upsert_item(item)

        tasks = [
            _upsert({
                "id": str(_uuid.uuid4()),
                "encounter_id": str(state.encounter_id),
                "agent_run_id": str(state.run_id),
                "source": ev.source,
                "document_id": ev.document_id,
                "excerpt": ev.excerpt[:2000],  # cap at 2 KB
                "relevance_score": ev.relevance_score,
                "cited_in": ev.cited_in,
            })
            for ev in state.evidence
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("cosmos write_evidence failed: %s", exc)


async def write_trace(
    state: AgentState,
    span_name: str,
    start_time: str,
    end_time: str,
    status: str = "OK",
    attributes: dict | None = None,
) -> None:
    """Write a single trace span."""
    container = _get_container("traces")
    if container is None:
        return
    try:
        import uuid as _uuid

        await container.upsert_item({
            "id": str(_uuid.uuid4()),
            "encounter_id": str(state.encounter_id),
            "run_id": str(state.run_id),
            "span_name": span_name,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "attributes": attributes or {},
        })
    except Exception as exc:  # noqa: BLE001
        log.warning("cosmos write_trace failed: %s", exc)
