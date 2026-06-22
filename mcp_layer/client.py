from mcp.types import TextContent
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from schemas.tool_result import ToolResult
from dataclasses import asdict


class MCPClient:

    async def call_tool(
            self,
            tool_name: str,
            arguments: dict
    ):

        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_layer.server"]
        )

        async with stdio_client(server_params) as (read, write):

            async with ClientSession(read, write) as session:

                await session.initialize()

                result = await session.call_tool(tool_name, arguments)

                tool_results = []
                for block in result.content:
                    if isinstance(block, TextContent): 
                        print(repr(block.text))
                        data = json.loads(block.text)
                        tool_results.append(
                            ToolResult(
                                source=data["source"],
                                title=data["title"],
                                content=data["content"],
                                url=data["url"],
                                metadata=data.get("metadata", {})
                            )
                        )

                return [asdict(item) for item in tool_results]