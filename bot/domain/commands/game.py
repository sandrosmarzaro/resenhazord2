import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.game_source import GameInfo, GameSource, IgdbSource, RawgSource

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
            flags=['show', 'dm'],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um jogo aleatório com capa e informações.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        for source in self._sources:
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
