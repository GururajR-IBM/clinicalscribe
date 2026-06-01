"""Tests for the ehr-mock MCP server."""

from __future__ import annotations

import json

import pytest

from ehr_mock.server import call_tool, list_tools


@pytest.mark.asyncio
async def test_list_tools_exposes_ehr_tools() -> None:
    tools = await list_tools()
    names = {t.name for t in tools}
    assert {"get_patient_history", "get_active_medications"} == names


@pytest.mark.asyncio
async def test_get_patient_history_known_patient() -> None:
    result = await call_tool("get_patient_history", {"patient_id": "PT-00123"})
    data = json.loads(result[0].text)
    assert data["patient_id"] == "PT-00123"
    assert isinstance(data["history"], list)
    assert len(data["history"]) >= 1
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_get_active_medications_known_patient() -> None:
    result = await call_tool("get_active_medications", {"patient_id": "PT-00456"})
    data = json.loads(result[0].text)
    assert data["patient_id"] == "PT-00456"
    meds = data["active_medications"]
    assert isinstance(meds, list)
    assert any(m["name"] == "Aspirin" for m in meds)


@pytest.mark.asyncio
async def test_unknown_patient_returns_error() -> None:
    result = await call_tool("get_patient_history", {"patient_id": "PT-UNKNOWN"})
    data = json.loads(result[0].text)
    assert "error" in data


@pytest.mark.asyncio
async def test_unknown_tool_returns_message() -> None:
    result = await call_tool("does_not_exist", {"patient_id": "PT-00123"})
    assert "Unknown tool" in result[0].text

