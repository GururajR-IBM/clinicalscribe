"""drug-interaction MCP server — Phase 2 (task 2.9).

Tool:
  check_combo — check potential interactions between two or more drugs
                using the openFDA Drug Label API (public, no key required).

Falls back to a known-interaction table when the network is unavailable.

OWASP A03: drug names are validated against a length cap and passed as
query parameters only — never interpolated into system prompts.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

_FDA_BASE = "https://api.fda.gov/drug/label.json"

# ── Known interaction table (fallback / augmentation) ─────────────────────────
# Format: frozenset({drug_a.lower(), drug_b.lower()}) -> interaction description
_KNOWN: dict[frozenset[str], str] = {
    frozenset({"warfarin", "aspirin"}): "Increased bleeding risk. Monitor INR closely.",
    frozenset({"warfarin", "ibuprofen"}): "NSAIDs increase bleeding risk with warfarin.",
    frozenset({"metformin", "alcohol"}): "Increased risk of lactic acidosis.",
    frozenset({"lisinopril", "potassium"}): "Risk of hyperkalaemia. Monitor electrolytes.",
    frozenset({"clopidogrel", "omeprazole"}): "Omeprazole reduces clopidogrel antiplatelet effect.",
    frozenset({"ssri", "tramadol"}): "Serotonin syndrome risk. Avoid combination.",
    frozenset({"methotrexate", "nsaid"}): "NSAIDs reduce methotrexate renal clearance — toxicity risk.",
    frozenset({"simvastatin", "amiodarone"}): "Increased myopathy/rhabdomyolysis risk.",
}


async def _openfda_interactions(drug_a: str, drug_b: str) -> list[str]:
    """Query openFDA for drug_warnings mentioning drug_b in drug_a's label."""
    query = f'drug_interactions:"{drug_b.lower()}"'
    params = {"search": f'openfda.brand_name:"{drug_a}" AND {query}', "limit": 3}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(_FDA_BASE, params=params)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()
        snippets: list[str] = []
        for result in data.get("results", []):
            interactions = result.get("drug_interactions", [])
            if isinstance(interactions, list):
                snippets.extend(interactions[:2])
        return snippets[:3]
    except (httpx.HTTPError, Exception):
        return []


server: Server = Server("clinicalscribe-drug-interaction")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="check_combo",
            description=(
                "Check for potential drug-drug interactions between two or more medications. "
                "Queries the openFDA Drug Label API and a curated interaction table. "
                "Returns a severity estimate and textual warnings. "
                "This is a demonstration tool — always verify with a clinical pharmacist."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "drugs": {
                        "type": "array",
                        "description": "List of drug names (generic or brand) to check.",
                        "items": {"type": "string", "minLength": 1, "maxLength": 100},
                        "minItems": 2,
                        "maxItems": 10,
                    },
                },
                "required": ["drugs"],
                "additionalProperties": False,
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name != "check_combo":
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    raw_drugs: list[str] = [str(d).strip() for d in arguments.get("drugs", [])]
    if len(raw_drugs) < 2:
        return [TextContent(type="text", text=json.dumps({"error": "Provide at least 2 drug names."}))]

    # Cap individual name length for safety
    drugs = [d[:100] for d in raw_drugs if d]
    interactions: list[dict[str, Any]] = []

    # Check all pairs
    for i in range(len(drugs)):
        for j in range(i + 1, len(drugs)):
            a, b = drugs[i].lower(), drugs[j].lower()
            pair_key = frozenset({a, b})

            # 1. Known table
            known = _KNOWN.get(pair_key)
            if known:
                interactions.append({
                    "drug_a": drugs[i],
                    "drug_b": drugs[j],
                    "severity": "moderate",
                    "source": "curated_table",
                    "description": known,
                })
                continue

            # 2. openFDA fallback
            snippets = await _openfda_interactions(a, b)
            if snippets:
                interactions.append({
                    "drug_a": drugs[i],
                    "drug_b": drugs[j],
                    "severity": "unknown",
                    "source": "openFDA",
                    "description": " | ".join(snippets),
                })

    result = {
        "drugs_checked": drugs,
        "interactions_found": len(interactions),
        "interactions": interactions,
        "disclaimer": "Demonstration only. Verify all interactions with a licensed pharmacist.",
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _main() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
