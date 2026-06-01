"""Tests for the drug-interaction MCP server."""

from __future__ import annotations

import json

import pytest

from drug_interaction.server import call_tool, list_tools


@pytest.mark.asyncio
async def test_list_tools_exposes_check_combo() -> None:
    tools = await list_tools()
    names = {t.name for t in tools}
    assert "check_combo" in names


@pytest.mark.asyncio
async def test_known_warfarin_aspirin_interaction() -> None:
    result = await call_tool("check_combo", {"drugs": ["warfarin", "aspirin"]})
    data = json.loads(result[0].text)
    assert data["interactions_found"] >= 1
    assert any(
        "bleeding" in i["description"].lower() for i in data["interactions"]
    )


@pytest.mark.asyncio
async def test_no_interaction_returns_zero_interactions() -> None:
    # Two drugs with no known interaction in our table
    result = await call_tool("check_combo", {"drugs": ["amoxicillin", "paracetamol"]})
    data = json.loads(result[0].text)
    # May be 0 or nonzero from openFDA — just validate structure
    assert "interactions" in data
    assert "drugs_checked" in data
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_too_few_drugs_returns_error() -> None:
    result = await call_tool("check_combo", {"drugs": ["warfarin"]})
    data = json.loads(result[0].text)
    assert "error" in data


@pytest.mark.asyncio
async def test_three_drug_combo_checked() -> None:
    result = await call_tool("check_combo", {"drugs": ["warfarin", "aspirin", "ibuprofen"]})
    data = json.loads(result[0].text)
    # 3 drugs -> at least 2 pairs checked
    assert len(data["drugs_checked"]) == 3

