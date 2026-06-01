import pytest

from drug_interaction.server import call_tool, list_tools


@pytest.mark.asyncio
async def test_list_tools_has_ping() -> None:
    tools = await list_tools()
    assert any(t.name == "ping" for t in tools)


@pytest.mark.asyncio
async def test_ping_returns_pong() -> None:
    result = await call_tool("ping", {})
    assert result[0].text == "pong"
