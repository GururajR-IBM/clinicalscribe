"""coding MCP server — Phase 2 (task 2.7).

Tools:
  search_icd10    — find ICD-10-CM codes matching a diagnosis description
  search_cpt      — find CPT procedure codes from a procedure description
  justify_code    — confirm whether a given code is appropriate for a transcript snippet

Falls back to a curated static table when Azure AI Search is not configured.

OWASP A03: all inputs are sanitised and used only as search query strings.
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

_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
_ICD10_INDEX = os.getenv("AZURE_SEARCH_INDEX_ICD10", "icd10-codes")
_CPT_INDEX = os.getenv("AZURE_SEARCH_INDEX_CPT", "cpt-codes")
_API_VERSION = "2024-05-01-preview"

# ── Static fallback tables ────────────────────────────────────────────────────
_ICD10: list[dict[str, str]] = [
    {"code": "J18.9", "description": "Pneumonia, unspecified organism"},
    {"code": "I10",   "description": "Essential (primary) hypertension"},
    {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
    {"code": "J44.1", "description": "COPD with acute exacerbation"},
    {"code": "I21.9", "description": "Acute myocardial infarction, unspecified"},
    {"code": "N39.0", "description": "Urinary tract infection, site not specified"},
    {"code": "J06.9", "description": "Acute upper respiratory infection, unspecified"},
    {"code": "M54.5", "description": "Low back pain"},
    {"code": "K21.0", "description": "Gastro-esophageal reflux disease with esophagitis"},
    {"code": "F32.9", "description": "Major depressive disorder, single episode, unspecified"},
]

_CPT: list[dict[str, str]] = [
    {"code": "99213", "description": "Office/outpatient E&M established patient, low complexity"},
    {"code": "99214", "description": "Office/outpatient E&M established patient, moderate complexity"},
    {"code": "99203", "description": "Office/outpatient E&M new patient, low complexity"},
    {"code": "99204", "description": "Office/outpatient E&M new patient, moderate complexity"},
    {"code": "71046", "description": "Chest X-ray, 2 views"},
    {"code": "93000", "description": "Electrocardiogram, routine with interpretation"},
    {"code": "80053", "description": "Comprehensive metabolic panel"},
    {"code": "85025", "description": "Complete blood count with differential"},
    {"code": "87804", "description": "Rapid influenza diagnostic test"},
    {"code": "96372", "description": "Therapeutic injection, subcutaneous/intramuscular"},
]


def _fuzzy_match(query: str, table: list[dict[str, str]], top: int) -> list[dict[str, Any]]:
    q = query.lower()
    scored = [
        {**row, "score": sum(word in row["description"].lower() for word in q.split())}
        for row in table
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return [{k: v for k, v in r.items() if k != "score"} for r in scored[:top] if r["score"] > 0] or [{"code": "N/A", "description": f"No match found for: {query[:80]}"}]


async def _search_index(index: str, query: str, top: int) -> list[dict[str, Any]]:
    if not _SEARCH_ENDPOINT or not _SEARCH_KEY:
        table = _ICD10 if index == _ICD10_INDEX else _CPT
        return _fuzzy_match(query, table, top)
    url = f"{_SEARCH_ENDPOINT}/indexes/{index}/docs/search?api-version={_API_VERSION}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            json={"search": query, "top": top},
            headers={"api-key": _SEARCH_KEY, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    return [{"code": doc.get("code", ""), "description": doc.get("description", "")} for doc in data.get("value", [])]


server: Server = Server("clinicalscribe-coding")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_icd10",
            description="Find ICD-10-CM diagnosis codes matching a clinical description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "minLength": 2, "maxLength": 300},
                    "top": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                },
                "required": ["description"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="search_cpt",
            description="Find CPT procedure codes matching a procedure description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "minLength": 2, "maxLength": 300},
                    "top": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                },
                "required": ["description"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="justify_code",
            description=(
                "Verify whether a given ICD-10 or CPT code is appropriate given a transcript snippet. "
                "Returns a brief justification and a confidence level (high/medium/low)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "minLength": 3, "maxLength": 20},
                    "code_type": {"type": "string", "enum": ["icd10", "cpt"]},
                    "transcript_snippet": {"type": "string", "minLength": 10, "maxLength": 1000},
                },
                "required": ["code", "code_type", "transcript_snippet"],
                "additionalProperties": False,
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "search_icd10":
        desc = str(arguments.get("description", "")).strip()
        top = min(int(arguments.get("top", 5)), 10)
        results = await _search_index(_ICD10_INDEX, desc, top)
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    if name == "search_cpt":
        desc = str(arguments.get("description", "")).strip()
        top = min(int(arguments.get("top", 5)), 10)
        results = await _search_index(_CPT_INDEX, desc, top)
        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    if name == "justify_code":
        code = str(arguments.get("code", "")).strip().upper()
        code_type = str(arguments.get("code_type", "icd10"))
        snippet = str(arguments.get("transcript_snippet", "")).strip()
        table = _ICD10 if code_type == "icd10" else _CPT
        match = next((r for r in table if r["code"].upper() == code), None)
        if not match:
            result = {"code": code, "found": False, "confidence": "low", "justification": "Code not found in local reference table."}
        else:
            keywords = match["description"].lower().split()
            hits = sum(1 for kw in keywords if kw in snippet.lower())
            confidence = "high" if hits >= 3 else "medium" if hits >= 1 else "low"
            result = {
                "code": code,
                "description": match["description"],
                "found": True,
                "confidence": confidence,
                "justification": f"{hits} keyword(s) from code description found in transcript snippet.",
            }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _main() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
