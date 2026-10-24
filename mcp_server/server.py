"""DrainFast MCP server: rain_forecast, tide_outlook and cell_history.

Each tool calls the same function in backend/sources.py that the API uses (tech.md
rule 11), so Kiro at build time and the co-pilot at run time see identical numbers.
Run: python -m mcp_server.server  (stdio)
"""
import asyncio
import json
import logging
from datetime import date
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from backend import sources

logging.basicConfig(level=logging.WARNING)  # stdout carries the MCP protocol; logs go to stderr
server = Server("drainfast-data")

_DATE_ARG = {"type": "object", "properties": {"date": {"type": "string", "format": "date",
             "description": "Local Boston date, YYYY-MM-DD"}}, "required": ["date"]}

TOOLS = [
    types.Tool(name="rain_forecast", inputSchema=_DATE_ARG,
               description="NWS forecast rain in inches for one Boston date. fallback=true if unavailable."),
    types.Tool(name="tide_outlook", inputSchema=_DATE_ARG,
               description="NOAA predicted high/low tides at Boston (8443970, ft MLLW) and the high-tide flag."),
    types.Tool(name="cell_history", description="311 storm reports in one ~100 m cell, newest first, with counts.",
               inputSchema={"type": "object", "properties": {"cell_id": {"type": "string"}}, "required": ["cell_id"]}),
]


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one tool call to backend.sources and return JSON-safe output."""
    if name == "rain_forecast":
        return sources.as_json(sources.rain_forecast(date.fromisoformat(arguments["date"])))
    if name == "tide_outlook":
        return sources.as_json(sources.tide_outlook(date.fromisoformat(arguments["date"])))
    if name == "cell_history":
        return sources.as_json(sources.cell_history(str(arguments["cell_id"])))
    raise ValueError(f"unknown tool: {name}")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """The three DrainFast data tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Run one tool in a worker thread and return its JSON result as text."""
    result = await asyncio.to_thread(run_tool, name, arguments or {})
    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


async def main() -> None:
    """Serve the tools over stdio."""
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
