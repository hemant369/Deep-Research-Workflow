from backend.mcp_layer.client import MCPClient
from backend.agents.base_agent import BaseAgent 
from backend.schemas.tool_result import ToolResult

class AcademicAgent(BaseAgent):

    def __init__(self):
        self.mcp_client = MCPClient()
    
    async def search(self, query: str) -> list[ToolResult]:
        print(f"AcademicAgent -> {query}")
        results = await self.mcp_client.call_tool(
            "arxiv_search",
            {
                "query": query
            }
        )
        return results
