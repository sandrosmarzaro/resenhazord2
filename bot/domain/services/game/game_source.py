from abc import ABC, abstractmethod

from bot.data.game_info import GameInfo


class GameSource(ABC):
    @abstractmethod
    async def fetch(self) -> GameInfo: ...
