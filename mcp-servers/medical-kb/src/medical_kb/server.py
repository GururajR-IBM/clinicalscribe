"""medical-kb MCP server — Phase 2 (task 2.6).

Tools:
  lookup_term   — search medical terminology / ICD descriptions in Azure AI Search
  verify_claim  — check whether a clinical claim is supported by indexed guidelines

Falls back to curated static data when AI Search is not configured (local dev).

OWASP A03: user input is used only as a search query string, never interpolated
into system prompts or SQL strings.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# ── Config from env ───────────────────────────────────────────────────────────
_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_MEDICAL_KB", "medical-kb")
_API_VERSION = "2024-05-01-preview"

# ── Static fallback for local dev ─────────────────────────────────────────────
_STATIC_KB: dict[str, str] = {
    "hypertension": "Persistently elevated arterial blood pressure (>=130/80 mmHg). ICD-10: I10.",
    "type 2 diabetes": "Chronic metabolic disorder from insulin resistance. ICD-10: E11.",
    "pneumonia": "Lung parenchyma infection, commonly bacterial. ICD-10: J18.9.",
    "copd": "Progressive airflow limitation from chronic lung inflammation. ICD-10: J44.1.",
    "acute myocardial infarction": "Cardiac myocyte death from prolonged ischaemia. ICD-10: I21.9.",
    "urinary tract infection": "Bacterial infection of the urinary tract. ICD-10: N39.0.",
    "community-acquired pneumonia": "Pneumonia acquired outside hospital. First-line: amoxicillin. ICD-10: J18.9.",
}


async def _search(query: str, top: int = 5) -> list[dict[str, Any]]:
    if not _SEARCH_ENDPOINT or not _SEARCH_KEY:
        q = query.lower()
        results = [
            {"term": k, "description": v, "score": 1.0}
            for k, v in _STATIC_KB.items()
            if any(word in k for word in q.split())
        ]
        return results[:top] if results else [{"term": query, "description": "No local match found.", "score": 0.0}]

    url = f"{_SEARCH_ENDPOINT}/indexes/{_INDEX_NAME}/docs/search?api-version={_API_VERSION}"
    payload = {
        "search": query,
        "top": top,
        "queryType": "semantic",
        "semanticConfiguration": "default",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"api-key": _SEARCH_KEY, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    return [
        {
            "term": doc.get("term", ""),
            "description": doc.get("description", ""),
            "score": doc.get("@search.score", 0),
        }
        for doc in data.get("value", [])
    ]


server: Server = Server("clinicalscribe-medical-kb")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="lookup_term",
            description=(
                "Search the curated medical knowledge base for a clinical term, condition, "
                "drug, or procedure. Returns up to 5 matching entries with ICD-10 codes "
                "and plain-language descriptions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "The clinical term, diagnosis, or keyword to look up.",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                    "top": {
                        "type": "integer",
                        "description": "Maximum results to return (1-10).",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["term"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="verify_claim",
            description=(
                "Check whether a clinical claim (e.g. 'amoxicillin is first-line for CAP') "
                "is supported by indexed clinical guidelines. Returns matched evidence or "
                "'no evidence found'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "The clinical claim to verify.",
                        "minLength": 5,
                        "maxLength": 500,
                    },
                },
                "required": ["claim"],
                "additionalProperties": False,
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "lookup_term":
        term = str(arguments.get("term", "")).strip()
        if not term:
            return [TextContent(type="text", text="Error: term is required.")]
        top = min(int(arguments.get("top", 5)), 10)
        results = await _search(term, top=top)
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    if name == "verify_claim":
        claim = str(arguments.get("claim", "")).strip()
        if not claim:
            return [TextContent(type="text", text="Error: claim is required.")]
        results = await _search(claim, top=3)
        supported = bool(results) and results[0].get("score", 0) >= 0.3
        return [TextContent(type="text", text=json.dumps({"supported": supported, "evidence": results}))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _main() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()

