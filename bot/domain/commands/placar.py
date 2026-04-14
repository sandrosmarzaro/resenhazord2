"""Live football matches from Transfermarkt."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    ParsedCommand,
    Platform,
)

if TYPE_CHECKING:
    from bot.domain.models.command_data import CommandData
    from bot.domain.models.football import TmLiveMatch
    from bot.domain.models.message import BotMessage
else:
    from bot.domain.models.command_data import CommandData
    from bot.domain.models.football import TmLiveMatch
    from bot.domain.models.message import BotMessage

from bot.domain.services.transfermarkt.service import TransfermarktService

_NUMBER_EMOJI = {
    0: '0️⃣',
    1: '1️⃣',
    2: '2️⃣',
    3: '3️⃣',
    4: '4️⃣',
    5: '5️⃣',
    6: '6️⃣',
    7: '7️⃣',
    8: '8️⃣',
    9: '9️⃣',
    10: '🔟',
}

_MAX_EMOJI_SCORE = 10


def _score_emoji(score: int | None) -> str:
    if score is None:
        return '-'
    if score <= _MAX_EMOJI_SCORE:
        return _NUMBER_EMOJI.get(score, str(score))
    return str(score)


class PlacarCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='placar',
            aliases=['score'],
            category=Category.OTHER,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Jogos de futebol ao vivo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        matches = await TransfermarktService.fetch_live_matches()

        if not matches:
            return [Reply.to(data).text('Nenhum jogo ao vivo agora. ✨')]

        by_comp: dict[str, list[TmLiveMatch]] = defaultdict(list)
        for m in matches:
            by_comp[m.competition_name].append(m)

        lines: list[str] = []
        for comp_name, comp_matches in sorted(by_comp.items()):
            first = comp_matches[0]
            lines.append(f'{first.country_flag_emoji} *{comp_name}*')
            for match in comp_matches:
                home = _score_emoji(match.home_score)
                away = _score_emoji(match.away_score)
                time = match.match_time
                lines.append(f'{match.home_team} {home} x {away} {match.away_team} ⏱️ {time}')
            lines.append('')

        caption = '\n'.join(lines).rstrip()
        return [Reply.to(data).text(caption)]
