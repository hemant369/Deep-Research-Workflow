from mcp_layer.client import MCPClient
from agents.base_agent import BaseAgent

class GeneralAgent(BaseAgent):

    def __init__(self):
        self.mcp_client = MCPClient()

    async def search(self, query: str):
        results = await self.mcp_client.call_tool(
            "web_search",
            {
                "query": query
            }
        )

        return results