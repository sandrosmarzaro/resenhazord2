import structlog

from bot.data.game_info import GameInfo
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.game_source import GameSource, IgdbSource, RawgSource

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
            options=[OptionDef(name='source', values=['rawg'])],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um jogo aleatório com capa e informações.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        sources = self._sources
        if parsed.options.get('source') == 'rawg':
            sources = [s for s in self._sources if isinstance(s, RawgSource)]

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
