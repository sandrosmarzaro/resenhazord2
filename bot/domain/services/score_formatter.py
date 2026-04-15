"""Format live match data for display."""

from datetime import UTC, date, datetime, timedelta

from bot.data.number_emoji import MAX_EMOJI_SCORE, NUMBER_EMOJI
from bot.domain.models.football import MatchStatus, TmLiveMatch


def score_emoji(score: int | None) -> str:
    if score is None:
        return '?'
    if score >= MAX_EMOJI_SCORE:
        return f'{score}'
    return NUMBER_EMOJI.get(score, str(score))


def format_match_time(match_time: str, status: MatchStatus) -> str:
    if status == MatchStatus.LIVE:
        return f'⏱️ {match_time}'
    return f'🕐 {match_time}'


def format_date_label(match_time: str) -> str:
    try:
        match_hour, match_minute = match_time.split(':')
        now = _get_current_datetime()
        match_dt = now.replace(hour=int(match_hour), minute=int(match_minute), second=0)
    except ValueError:
        return ''
    if match_dt < now:
        return 'Hoje'
    if (match_dt - now) < timedelta(days=1):
        return 'Hoje'
    return match_dt.strftime('%d/%m')


def format_live_row(match: TmLiveMatch) -> str:
    home = score_emoji(match.home_score)
    away = score_emoji(match.away_score)
    time_str = format_match_time(match.match_time, match.status)
    return f'_{match.home_team}_ {home} x {away} _{match.away_team}_\n{time_str}'


def format_upcoming_row(match: TmLiveMatch) -> str:
    date_label = format_date_label(match.match_time)
    time_str = format_match_time(match.match_time, match.status)
    date_str = f'{date_label} ' if date_label else ''
    return f'_{match.home_team}_ - x - _{match.away_team}_\n{date_str}{time_str}'


def format_finished_row(match: TmLiveMatch) -> str:
    home = score_emoji(match.home_score)
    away = score_emoji(match.away_score)
    return f'_{match.home_team}_ {home} x {away} _{match.away_team}_'


def group_by_competition(matches: list[TmLiveMatch]) -> list[list[TmLiveMatch]]:
    groups: dict[str, list[TmLiveMatch]] = {}
    for m in matches:
        key = m.competition_name
        groups.setdefault(key, []).append(m)
    return list(groups.values())


def apply_soft_cap(matches: list[TmLiveMatch], soft_cap: int) -> list[TmLiveMatch]:
    picked: list[TmLiveMatch] = []
    for group in group_by_competition(matches):
        if len(picked) >= soft_cap:
            break
        picked.extend(group)
    return picked


def build_section(title: str, matches: list[TmLiveMatch], row_formatter: callable) -> list[str]:
    lines = [title]
    for group in group_by_competition(matches):
        head = group[0]
        lines.append(f'{head.country_flag_emoji} *{head.competition_name}*')
        lines.extend(row_formatter(m) for m in group)
        lines.append('')
    return lines


def is_within_upcoming_window(match_time: str, window_hours: int) -> bool:
    if not match_time or ':' not in match_time:
        return False
    try:
        hour, minute = match_time.split(':')
        hour_int, minute_int = int(hour), int(minute)
    except ValueError:
        return False
    now = _get_current_datetime()
    match_dt = now.replace(hour=hour_int, minute=minute_int, second=0)
    if match_dt < now:
        match_dt += timedelta(days=1)
    return (match_dt - now) <= timedelta(hours=window_hours)


def _get_current_datetime() -> datetime:
    return datetime.now(UTC)


def _get_current_date() -> date:
    return datetime.now(UTC).date()
