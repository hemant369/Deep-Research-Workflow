from backend.mcp_layer.client import MCPClient
from backend.agents.base_agent import BaseAgent
from backend.schemas.tool_result import ToolResult

class GeneralAgent(BaseAgent):

    def __init__(self):
        self.mcp_client = MCPClient()

    async def search(self, query: str) -> list[ToolResult]:
        print(f"GenerallAgent -> {query}")
        results = await self.mcp_client.call_tool(
            "web_search",
            {
                "query": query
            }
        )

        return results
