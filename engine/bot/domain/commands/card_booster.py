"""Base class for card game commands with booster pack support."""

from abc import abstractmethod
from dataclasses import dataclass

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient
from bot.services.card_grid_builder import build_card_grid


@dataclass(frozen=True)
class CardItem:
    image_url: str
    label: str


@dataclass(frozen=True)
class BoosterConfig:
    count: int = 6
    columns: int = 3
    cell_width: int = 300
    cell_height: int = 420


class CardBoosterCommand(Command):
    BOOSTER_CONFIG = BoosterConfig()

    @abstractmethod
    async def _fetch_booster_items(self) -> list[CardItem]: ...

    async def _run_booster(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        items = await self._fetch_booster_items()
        cfg = self.BOOSTER_CONFIG

        image_buffers = [await HttpClient.get_buffer(item.image_url) for item in items]
        grid_buffer = build_card_grid(
            image_buffers,
            columns=cfg.columns,
            cell_width=cfg.cell_width,
            cell_height=cfg.cell_height,
        )

        caption = '\n\n'.join(f'*{i + 1}.* {item.label}' for i, item in enumerate(items))
        return [Reply.to(data).image_buffer(grid_buffer, caption)]
