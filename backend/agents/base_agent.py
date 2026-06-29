from abc import ABC, abstractmethod
from backend.schemas.tool_result import ToolResult


class BaseAgent(ABC):

    @abstractmethod
    async def search(
        self,
        query: str
    ) -> list[ToolResult]:
        pass
