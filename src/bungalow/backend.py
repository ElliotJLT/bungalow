"""The seam between bungalow and the MCP.

Everything the product knows about a property comes through a `ToolBackend`. The
product never calls SRA, computes stamp duty, or hardcodes a lease rule. It asks
the backend, and the backend asks the homebuyer-mcp. This is the line that keeps
the MCP the source of truth and the product a thin, honest presenter.

Two backends ship:

    MCPBackend     talks to the running homebuyer-mcp server (stdio).
    StaticBackend  replays recorded tool outputs, for tests and the sample.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolBackend(Protocol):
    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]: ...


class StaticBackend:
    """Replay recorded MCP outputs, keyed by tool name.

    Used by the tests and to render the shipped sample from real, captured MCP
    responses, so the product can be exercised end to end without a live server
    or API keys.
    """

    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self._responses = responses

    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        if tool not in self._responses:
            raise KeyError(f"no recorded response for tool {tool!r}")
        return self._responses[tool]


class MCPBackend:
    """Call tools on the running homebuyer-mcp server over stdio.

    Requires the `mcp` extra and the server on PATH (default `python -m
    clearbook`). A session is opened per call, which is simple and fine for a
    report's handful of calls. This path needs a live server, so it is exercised
    manually rather than in the unit tests.
    """

    def __init__(self, command: str = "python", args: list[str] | None = None) -> None:
        self.command = command
        self.args = args if args is not None else ["-m", "clearbook"]

    def call(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        import asyncio

        return asyncio.run(self._call_async(tool, params))

    async def _call_async(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:  # pragma: no cover - import guard
            raise ImportError(
                "MCPBackend needs the mcp extra: pip install 'bungalow[mcp]'"
            ) from exc

        server = StdioServerParameters(command=self.command, args=self.args)
        async with (
            stdio_client(server) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(tool, params)
            return _parse_tool_result(result)


def _parse_tool_result(result: Any) -> dict[str, Any]:
    """Pull the JSON payload out of an MCP tool result's text content."""
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        if text:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
    raise ValueError("MCP tool returned no JSON object")
