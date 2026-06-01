"""Tests for the coding MCP server."""

from __future__ import annotations

import json

import pytest

from coding.server import call_tool, list_tools


@pytest.mark.asyncio
async def test_list_tools_exposes_three_tools() -> None:
    tools = await list_tools()
    names = {t.name for t in tools}
    assert {"search_icd10", "search_cpt", "justify_code"} == names


@pytest.mark.asyncio
async def test_search_icd10_returns_codes() -> None:
    result = await call_tool("search_icd10", {"description": "pneumonia"})
    data = json.loads(result[0].text)
    assert isinstance(data, list)
    assert any(row["code"].startswith("J") for row in data)


@pytest.mark.asyncio
async def test_search_cpt_returns_codes() -> None:
    result = await call_tool("search_cpt", {"description": "chest x-ray"})
    data = json.loads(result[0].text)
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_justify_code_high_confidence() -> None:
    result = await call_tool(
        "justify_code",
        {
            "code": "J18.9",
            "code_type": "icd10",
            "transcript_snippet": "Patient has pneumonia in the lung, unspecified organism suspected.",
        },
    )
    data = json.loads(result[0].text)
    assert data["found"] is True
    assert data["confidence"] in {"high", "medium", "low"}


@pytest.mark.asyncio
async def test_justify_code_not_found() -> None:
    result = await call_tool(
        "justify_code",
        {"code": "ZZZZ", "code_type": "icd10", "transcript_snippet": "Some text."},
    )
    data = json.loads(result[0].text)
    assert data["found"] is False
    assert data["confidence"] == "low"

