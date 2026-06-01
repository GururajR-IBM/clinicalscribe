"""Tests for the medical-kb MCP server."""

from __future__ import annotations

import pytest

from medical_kb.server import call_tool, list_tools


@pytest.mark.asyncio
async def test_list_tools_exposes_lookup_and_verify() -> None:
    tools = await list_tools()
    names = {t.name for t in tools}
    assert "lookup_term" in names
    assert "verify_claim" in names


@pytest.mark.asyncio
async def test_lookup_term_returns_results() -> None:
    result = await call_tool("lookup_term", {"term": "pneumonia"})
    assert result
    import json
    data = json.loads(result[0].text)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "description" in data[0]


@pytest.mark.asyncio
async def test_verify_claim_with_known_claim() -> None:
    result = await call_tool("verify_claim", {"claim": "amoxicillin first-line community-acquired pneumonia"})
    import json
    data = json.loads(result[0].text)
    assert "supported" in data
    assert "evidence" in data


@pytest.mark.asyncio
async def test_lookup_term_empty_returns_error() -> None:
    result = await call_tool("lookup_term", {"term": ""})
    assert "Error" in result[0].text


@pytest.mark.asyncio
async def test_unknown_tool_returns_message() -> None:
    result = await call_tool("does_not_exist", {})
    assert "Unknown tool" in result[0].text

    result = await call_tool("ping", {})
    assert result[0].text == "pong"
