from typing import TYPE_CHECKING

import structlog

from bot.data.game_info import GameInfo
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    Flag,
    OptionDef,
    ParsedCommand,
    Platform,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.game.igdb_source import IgdbSource
from bot.domain.services.game.rawg_source import RawgSource

if TYPE_CHECKING:
    from bot.domain.services.game.game_source import GameSource

logger = structlog.get_logger()


class GameCommand(Command):
    def __init__(
        self,
        twitch_client_id: str = '',
        twitch_client_secret: str = '',
        rawg_api_key: str = '',
    ) -> None:
        super().__init__()
        self._sources: list[GameSource] = [
            IgdbSource(twitch_client_id, twitch_client_secret),
            RawgSource(rawg_api_key),
        ]

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='game',
            flags=[Flag.SHOW, Flag.DM],
            options=[OptionDef(name='source', values=['rawg', 'igdb'])],
            category=Category.RANDOM,
            platforms=[Platform.WHATSAPP, Platform.DISCORD, Platform.TELEGRAM],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um jogo aleatório com capa e informações.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        source_opt = parsed.options.get('source')
        if source_opt == 'rawg':
            sources = [s for s in self._sources if isinstance(s, RawgSource)]
        elif source_opt == 'igdb':
            sources = [s for s in self._sources if isinstance(s, IgdbSource)]
        else:
            sources = self._sources

        for source in sources:
            try:
                game = await source.fetch()
                caption = self._build_caption(game)
                return [Reply.to(data).image(game.cover_url, caption)]
            except Exception:
                logger.exception('game_source_error', source=source.__class__.__name__)
                continue
        return [Reply.to(data).text('Erro ao buscar jogo. Tente novamente mais tarde! 🎮')]

    @staticmethod
    def _build_caption(game: GameInfo) -> str:
        lines = [
            f'🎮 *{game.name}* ({game.year})',
            '',
            f'🏷️ {game.genres}',
            f'🖥️ {game.platforms}',
        ]
        if game.rating:
            lines.append(f'⭐ {game.rating}')
        return '\n'.join(lines)
