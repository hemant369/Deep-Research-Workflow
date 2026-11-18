import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from schemas.tool_result import ToolResult, normalize_tool_results


class MCPClient:
    """Small client used by LangGraph nodes to call local MCP search tools."""

    async def search_batch(
        self,
        tool_name: str,
        queries: list[str],
    ) -> tuple[list[ToolResult], list[dict[str, str]]]:
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_layer.server"],
        )

        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.call_tool(tool_name, {"queries": queries})

        for block in response.content:
            if not isinstance(block, TextContent):
                continue

            payload = json.loads(block.text)
            if isinstance(payload, dict):
                return (
                    normalize_tool_results(payload.get("results", [])),
                    [
                        error
                        for error in payload.get("errors", [])
                        if isinstance(error, dict)
                    ],
                )

        return [], []
