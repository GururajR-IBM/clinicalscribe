"""ehr-mock MCP server — Phase 2 (task 2.8).

Exposes read-only synthetic EHR data for demonstration purposes.
All data is entirely fictional. Never used with real patient records.

Tools:
  get_patient_history     — retrieve past diagnoses and visit summaries
  get_active_medications  — list current active medications for a patient
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# ── Synthetic patient database (demo only) ─────────────────────────────────────
_PATIENTS: dict[str, dict[str, Any]] = {
    "PT-00123": {
        "name": "Jane Demo",
        "dob": "1975-04-12",
        "history": [
            {"date": "2025-11-10", "diagnosis": "Community-acquired pneumonia (J18.9)", "provider": "Dr. Smith"},
            {"date": "2025-06-02", "diagnosis": "Essential hypertension (I10)", "provider": "Dr. Patel"},
            {"date": "2024-09-15", "diagnosis": "Type 2 diabetes mellitus (E11.9)", "provider": "Dr. Patel"},
        ],
        "medications": [
            {"name": "Metformin", "dose": "500 mg", "frequency": "twice daily", "started": "2024-09-20"},
            {"name": "Lisinopril", "dose": "10 mg", "frequency": "once daily", "started": "2025-06-10"},
            {"name": "Atorvastatin", "dose": "20 mg", "frequency": "once daily at bedtime", "started": "2025-06-10"},
        ],
    },
    "PT-00456": {
        "name": "John Demo",
        "dob": "1960-08-23",
        "history": [
            {"date": "2026-01-05", "diagnosis": "COPD with acute exacerbation (J44.1)", "provider": "Dr. Lee"},
            {"date": "2025-03-14", "diagnosis": "Acute myocardial infarction (I21.9)", "provider": "Dr. Nguyen"},
        ],
        "medications": [
            {"name": "Tiotropium", "dose": "18 mcg", "frequency": "once daily inhaled", "started": "2026-01-10"},
            {"name": "Aspirin", "dose": "81 mg", "frequency": "once daily", "started": "2025-03-20"},
            {"name": "Clopidogrel", "dose": "75 mg", "frequency": "once daily", "started": "2025-03-20"},
            {"name": "Metoprolol", "dose": "25 mg", "frequency": "twice daily", "started": "2025-03-20"},
        ],
    },
}


server: Server = Server("clinicalscribe-ehr-mock")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_patient_history",
            description=(
                "Retrieve the past diagnosis history and visit summaries for a patient. "
                "All data is synthetic — for demonstration only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Patient identifier (e.g. PT-00123).",
                        "minLength": 1,
                        "maxLength": 50,
                    },
                },
                "required": ["patient_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_active_medications",
            description=(
                "Return the current active medication list for a patient. "
                "All data is synthetic — for demonstration only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Patient identifier (e.g. PT-00123).",
                        "minLength": 1,
                        "maxLength": 50,
                    },
                },
                "required": ["patient_id"],
                "additionalProperties": False,
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    patient_id = str(arguments.get("patient_id", "")).strip()
    patient = _PATIENTS.get(patient_id)

    if name == "get_patient_history":
        if not patient:
            return [TextContent(type="text", text=json.dumps({"error": f"Patient {patient_id} not found in mock EHR."}))]
        return [TextContent(type="text", text=json.dumps({
            "patient_id": patient_id,
            "name": patient["name"],
            "dob": patient["dob"],
            "history": patient["history"],
            "disclaimer": "Synthetic data only. Not for clinical use.",
        }, indent=2))]

    if name == "get_active_medications":
        if not patient:
            return [TextContent(type="text", text=json.dumps({"error": f"Patient {patient_id} not found in mock EHR."}))]
        return [TextContent(type="text", text=json.dumps({
            "patient_id": patient_id,
            "name": patient["name"],
            "active_medications": patient["medications"],
            "disclaimer": "Synthetic data only. Not for clinical use.",
        }, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _main() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
