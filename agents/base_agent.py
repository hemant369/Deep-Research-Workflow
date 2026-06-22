from abc import ABC, abstractmethod


class BaseAgent(ABC):

    @abstractmethod
    async def search(
        self,
        query: str
    ):
        pass