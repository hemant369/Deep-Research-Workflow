from mcp_layer.client import MCPClient
from agents.base_agent import BaseAgent 

class AcademicAgent(BaseAgent):

    def __init__(self):
        self.mcp_client = MCPClient()
    
    async def search(self, query: str):
        print(f"AcademicAgent -> {query}")
        results = await self.mcp_client.call_tool(
            "arxiv_search",
            {
                "query": query
            }
        )
        return results