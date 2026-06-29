from mcp.types import TextContent
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from backend.schemas.tool_result import ToolResult, normalize_tool_results


class MCPClient:

    async def call_tool(
            self,
            tool_name: str,
            arguments: dict
    ) -> list[ToolResult]:

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "backend.mcp_layer.server"]
        )

        async with stdio_client(server_params) as (read, write):

            async with ClientSession(read, write) as session:

                await session.initialize()

                result = await session.call_tool(tool_name, arguments)

                tool_results: list[ToolResult] = []
                for block in result.content:
                    if isinstance(block, TextContent): 
                        print(repr(block.text))
                        data = json.loads(block.text)
                        tool_results.extend(normalize_tool_results(data))

                return tool_results
