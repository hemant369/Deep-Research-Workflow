from mcp_layer.client import MCPClient
from agents.base_agent import BaseAgent 


class CodingAgent(BaseAgent):

    def __init__(self):
        self.mcp_client = MCPClient()

    async def search(self, query: str):
        print(f"CodingAgent -> {query}")
        results = await self.mcp_client.call_tool(
            "github_search",
            {
                "query": query
            }
        )

        return results