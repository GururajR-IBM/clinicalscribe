"""drug-interaction MCP server. Phase 0 stub."""

from __future__ import annotations

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

server: Server = Server("clinicalscribe-drug-interaction")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ping",
            description="Health check. Returns 'pong'.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, object]) -> list[TextContent]:
    if name == "ping":
        return [TextContent(type="text", text="pong")]
    raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
