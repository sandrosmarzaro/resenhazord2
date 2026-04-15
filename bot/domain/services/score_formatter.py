"""Format live match data for display."""

from datetime import UTC, date, datetime, timedelta

from bot.data.football_league_priority import league_priority
from bot.data.number_emoji import MAX_EMOJI_SCORE, NUMBER_EMOJI
from bot.domain.models.football import MatchStatus, TmLiveMatch


def score_emoji(score: int | None) -> str:
    if score is None:
        return '-'
    if score > MAX_EMOJI_SCORE:
        return f'{score}'
    if score == MAX_EMOJI_SCORE:
        return '🔟'
    return NUMBER_EMOJI.get(score, str(score))


def format_match_time(match_time: str, status: MatchStatus) -> str:
    if status == MatchStatus.LIVE:
        return f'⏱️ {match_time}'
    return f'🕐 {match_time}'


def format_date_label(match_time: str) -> str:
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
    groups = group_by_competition(matches)
    groups.sort(key=lambda g: (league_priority(g[0].competition_code), g[0].competition_name))
    picked: list[TmLiveMatch] = []
    for group in groups:
        if len(picked) >= soft_cap:
            break
        picked.extend(group)
    return picked


def build_section(title: str, matches: list[TmLiveMatch], row_formatter: callable) -> list[str]:
    groups = group_by_competition(matches)
    groups.sort(key=lambda g: (league_priority(g[0].competition_code), g[0].competition_name))
    lines = [title]
    for group in groups:
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
