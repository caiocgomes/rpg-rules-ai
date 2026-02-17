from abc import ABC, abstractmethod

from caprag.schemas import State


class RetrievalStrategy(ABC):
    @abstractmethod
    async def execute(self, state: State) -> dict:
        ...
