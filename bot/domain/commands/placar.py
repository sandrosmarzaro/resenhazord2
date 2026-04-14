"""Live football matches from Transfermarkt."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
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
    from bot.domain.models.football import MatchStatus, TmLiveMatch
    from bot.domain.models.message import BotMessage
else:
    from bot.domain.models.command_data import CommandData
    from bot.domain.models.football import MatchStatus, TmLiveMatch
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


def _get_current_datetime() -> datetime:
    return datetime.now(UTC)


def _get_current_date() -> date:
    return datetime.now(UTC).date()


def _format_match_time(match_time: str, status: MatchStatus) -> str:
    if status == MatchStatus.LIVE:
        return f'⏱️ {match_time}'
    return f'🕐 {match_time}'


def _format_date_label(match_time: str) -> str:
    try:
        match_hour, match_minute = match_time.split(':')
        now = _get_current_datetime()
        match_dt = now.replace(
            hour=int(match_hour), minute=int(match_minute), second=0, microsecond=0
        )
        today = _get_current_date()
        match_date = match_dt.date()

        if match_date == today:
            return 'Hoje'
        tomorrow = today.replace(day=today.day + 1)
        if match_date == tomorrow:
            return 'Amanhã'
        return match_date.strftime('%d/%m')
    except (ValueError, AttributeError):
        return ''


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

        live_matches = [m for m in matches if m.status == MatchStatus.LIVE]
        upcoming_matches = [m for m in matches if m.status == MatchStatus.NOT_STARTED]

        lines: list[str] = []

        if live_matches:
            lines.append('🔥 *Ao Vivo*\n')
            by_comp: dict[str, list[TmLiveMatch]] = defaultdict(list)
            for m in live_matches:
                by_comp[m.competition_name].append(m)
            for comp_name, comp_matches in sorted(by_comp.items()):
                first = comp_matches[0]
                lines.append(f'{first.country_flag_emoji} *{comp_name}*')
                for match in comp_matches:
                    home = _score_emoji(match.home_score)
                    away = _score_emoji(match.away_score)
                    time_str = _format_match_time(match.match_time, match.status)
                    lines.append(f'{match.home_team} {home} x {away} {match.away_team} {time_str}')
                lines.append('')

        if upcoming_matches:
            lines.append('📅 *Próximos Jogos*\n')
            by_comp = defaultdict(list)
            for m in upcoming_matches:
                by_comp[m.competition_name].append(m)
            for comp_name, comp_matches in sorted(by_comp.items()):
                first = comp_matches[0]
                lines.append(f'{first.country_flag_emoji} *{comp_name}*')
                for match in comp_matches:
                    date_label = _format_date_label(match.match_time)
                    time_str = _format_match_time(match.match_time, match.status)
                    date_str = f'{date_label} ' if date_label else ''
                    lines.append(
                        f'{match.home_team} - x - {match.away_team} {date_str}{time_str}'
                    )
                lines.append('')

        caption = '\n'.join(lines).rstrip()
        return [Reply.to(data).text(caption)]
