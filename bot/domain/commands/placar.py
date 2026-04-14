"""Live football matches from Transfermarkt."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
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
    from collections.abc import Callable

    from bot.domain.models.command_data import CommandData
    from bot.domain.models.football import MatchStatus, TmLiveMatch
    from bot.domain.models.message import BotMessage
else:
    from bot.domain.models.command_data import CommandData
    from bot.domain.models.football import MatchStatus, TmLiveMatch
    from bot.domain.models.message import BotMessage

from bot.data.football_league_priority import league_priority
from bot.data.number_emoji import MAX_EMOJI_SCORE, NUMBER_EMOJI
from bot.domain.services.transfermarkt.service import TransfermarktService

_UPCOMING_WINDOW_HOURS = 6
_SECTION_SOFT_CAP = 7


def _get_current_datetime() -> datetime:
    return datetime.now(UTC)


def _get_current_date() -> date:
    return datetime.now(UTC).date()


def _is_within_upcoming_window(match_time: str) -> bool:
    if not match_time or ':' not in match_time:
        return False
    try:
        hour, minute = match_time.split(':')
        hour_int, minute_int = int(hour), int(minute)
    except ValueError:
        return False
    now = _get_current_datetime()
    candidate = now.replace(hour=hour_int, minute=minute_int, second=0, microsecond=0)
    if candidate < now:
        candidate += timedelta(days=1)
    delta = candidate - now
    return delta <= timedelta(hours=_UPCOMING_WINDOW_HOURS)


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
        tomorrow = today + timedelta(days=1)
        if match_date == tomorrow:
            return 'Amanhã'
        return match_date.strftime('%d/%m')
    except (ValueError, AttributeError):
        return ''


def _score_emoji(score: int | None) -> str:
    if score is None:
        return '-'
    if score <= MAX_EMOJI_SCORE:
        return NUMBER_EMOJI.get(score, str(score))
    return str(score)


class PlacarCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='placar',
            aliases=['score'],
            flags=['past', 'now', 'next'],
            category=Category.OTHER,
            platforms=[Platform.WHATSAPP, Platform.DISCORD],
        )

    @property
    def menu_description(self) -> str:
        return 'Jogos de futebol ao vivo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        matches = await TransfermarktService.fetch_live_matches()

        show_past = 'past' in parsed.flags
        show_now = 'now' in parsed.flags
        show_next = 'next' in parsed.flags
        if not (show_past or show_now or show_next):
            show_past = show_now = show_next = True

        live_all = [m for m in matches if m.status == MatchStatus.LIVE] if show_now else []
        upcoming_all = (
            [
                m
                for m in matches
                if m.status == MatchStatus.NOT_STARTED and _is_within_upcoming_window(m.match_time)
            ]
            if show_next
            else []
        )
        finished_all = [m for m in matches if m.status == MatchStatus.FINISHED] if show_past else []
        live_matches = _apply_soft_cap(live_all, _SECTION_SOFT_CAP)
        upcoming_matches = _apply_soft_cap(upcoming_all, _SECTION_SOFT_CAP)
        finished_matches = _apply_soft_cap(finished_all, _SECTION_SOFT_CAP)

        if not live_matches and not upcoming_matches and not finished_matches:
            return [Reply.to(data).text('Nenhum jogo ao vivo agora. ✨')]

        lines: list[str] = []
        if live_matches:
            lines.extend(_build_section('🔥 *Ao Vivo*\n', live_matches, _format_live_row))
        if upcoming_matches:
            lines.extend(
                _build_section('📅 *Próximos Jogos*\n', upcoming_matches, _format_upcoming_row)
            )
        if finished_matches:
            lines.extend(
                _build_section('✅ *Últimos Resultados*\n', finished_matches, _format_finished_row)
            )

        caption = '\n'.join(lines).rstrip()
        return [Reply.to(data).text(caption)]


def _group_by_competition(matches: list[TmLiveMatch]) -> list[list[TmLiveMatch]]:
    by_code: dict[str, list[TmLiveMatch]] = defaultdict(list)
    for m in matches:
        by_code[m.competition_code].append(m)
    return sorted(
        by_code.values(),
        key=lambda g: (league_priority(g[0].competition_code), g[0].competition_name),
    )


def _build_section(
    header: str,
    matches: list[TmLiveMatch],
    row_formatter: Callable[[TmLiveMatch], str],
) -> list[str]:
    lines: list[str] = [header]
    for group in _group_by_competition(matches):
        head = group[0]
        lines.append(f'{head.country_flag_emoji} *{head.competition_name}*')
        lines.extend(row_formatter(m) for m in group)
        lines.append('')
    return lines


def _apply_soft_cap(matches: list[TmLiveMatch], soft_cap: int) -> list[TmLiveMatch]:
    picked: list[TmLiveMatch] = []
    for group in _group_by_competition(matches):
        if len(picked) >= soft_cap:
            break
        picked.extend(group)
    return picked


def _format_live_row(match: TmLiveMatch) -> str:
    home = _score_emoji(match.home_score)
    away = _score_emoji(match.away_score)
    time_str = _format_match_time(match.match_time, match.status)
    return f'_{match.home_team}_ {home} x {away} _{match.away_team}_\n{time_str}'


def _format_upcoming_row(match: TmLiveMatch) -> str:
    date_label = _format_date_label(match.match_time)
    time_str = _format_match_time(match.match_time, match.status)
    date_str = f'{date_label} ' if date_label else ''
    return f'_{match.home_team}_ - x - _{match.away_team}_\n{date_str}{time_str}'


def _format_finished_row(match: TmLiveMatch) -> str:
    home = _score_emoji(match.home_score)
    away = _score_emoji(match.away_score)
    return f'_{match.home_team}_ {home} x {away} _{match.away_team}_'
