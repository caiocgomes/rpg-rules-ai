from abc import ABC, abstractmethod

from rpg_rules_ai.schemas import State


class RetrievalStrategy(ABC):
    @abstractmethod
    async def execute(self, state: State) -> dict:
        ...
