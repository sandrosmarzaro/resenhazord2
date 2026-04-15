"""Match result/status parsing for live matches."""

import re
from typing import ClassVar

from bs4 import Tag

from bot.domain.models.football import MatchStatus
from bot.domain.services.transfermarkt.parse_helpers import ParseHelpers


class MatchResultParser(ParseHelpers):
    _score_parts_count: ClassVar[int] = 2
    _time_format_length: ClassVar[int] = 5
    _max_hour: ClassVar[int] = 23
    _max_minute: ClassVar[int] = 59
    _match_id_re_v1: ClassVar[re.Pattern[str]] = re.compile(r'/spielbericht/(\d+)')
    _match_id_re_v2: ClassVar[re.Pattern[str]] = re.compile(r'/ticker/begegnung/live/(\d+)')
    _minute_re: ClassVar[re.Pattern[str]] = re.compile(r'(\d+)')

    @classmethod
    def parse_match_result(
        cls, result_link: Tag, result_cell: Tag, time_cell: Tag | None = None
    ) -> tuple[int | None, int | None, MatchStatus, str]:
        result_text = cls._extract_result_text(result_link)
        title = str(result_link.get('title') or '')
        status_from_title = cls._get_match_status_from_title(title)

        if cls._is_finished_result(result_link):
            home, away = cls._parse_score_parts(result_text)
            return (home, away, MatchStatus.FINISHED, result_text)

        if status_from_title == MatchStatus.NOT_STARTED:
            match_time = cls._extract_match_time(result_cell)
            if not match_time and cls._looks_like_scheduled_time(result_text):
                match_time = result_text
            return (None, None, MatchStatus.NOT_STARTED, match_time)

        if status_from_title == MatchStatus.LIVE or cls._is_live_score(result_text):
            parsed = cls._try_parse_live_score(result_text, result_cell, time_cell)
            if parsed is not None:
                return parsed
            return (None, None, MatchStatus.LIVE, result_text)

        return (None, None, MatchStatus.NOT_STARTED, result_text)

    @classmethod
    def _is_finished_result(cls, result_link: Tag) -> bool:
        span = result_link.find('span', class_='matchresult')
        if not span or not isinstance(span, Tag):
            return False
        return 'finished' in (span.get('class') or [])

    @classmethod
    def _parse_score_parts(cls, result_text: str) -> tuple[int | None, int | None]:
        separator = ' - ' if ' - ' in result_text else ':'
        parts = result_text.split(separator)
        if len(parts) != cls._score_parts_count:
            return (None, None)
        try:
            return (int(parts[0].strip()), int(parts[1].strip()))
        except ValueError:
            return (None, None)

    @classmethod
    def _try_parse_live_score(
        cls, result_text: str, result_cell: Tag, time_cell: Tag | None
    ) -> tuple[int, int, MatchStatus, str] | None:
        if not cls._is_live_score(result_text):
            return None
        separator = ' - ' if ' - ' in result_text else ':'
        parts = result_text.split(separator)
        if len(parts) != cls._score_parts_count:
            return None
        try:
            home = int(parts[0].strip())
            away = int(parts[1].strip())
        except ValueError:
            return None
        match_time = cls._extract_match_time_from_row(time_cell) or cls._extract_match_time(
            result_cell
        )
        return (home, away, MatchStatus.LIVE, match_time)

    @staticmethod
    def _extract_match_id(result_link: Tag) -> str:
        match_id_href = result_link.get('href', '')
        if match_id_href:
            mid_match = MatchResultParser._match_id_re_v1.search(str(match_id_href))
            if mid_match:
                return mid_match.group(1)
            mid_match = MatchResultParser._match_id_re_v2.search(str(match_id_href))
            if mid_match:
                return mid_match.group(1)
        return ''

    @staticmethod
    def _extract_result_text(link: Tag) -> str:
        match_result_span = link.find('span', class_='matchresult')
        if match_result_span and isinstance(match_result_span, Tag):
            return match_result_span.get_text(strip=True)
        return link.get_text(strip=True)

    @staticmethod
    def _is_live_score(result_text: str) -> bool:
        if not result_text or not result_text[0].isdigit():
            return False
        if len(result_text) == MatchResultParser._time_format_length and result_text[2] == ':':
            return False
        if ':' in result_text:
            parts = result_text.split(':')
            is_digit = parts[0].isdigit() and parts[1].isdigit()
            if len(parts) == MatchResultParser._score_parts_count and is_digit:
                return True
        return ' - ' in result_text

    @staticmethod
    def _looks_like_scheduled_time(text: str) -> bool:
        if not text or len(text) != MatchResultParser._time_format_length or text[2] != ':':
            return False
        try:
            hour, minute = text.split(':')
            hour_int, minute_int = int(hour), int(minute)
        except ValueError:
            return False
        max_hour = MatchResultParser._max_hour
        max_minute = MatchResultParser._max_minute
        return 0 <= hour_int <= max_hour and 0 <= minute_int <= max_minute

    @staticmethod
    def _get_match_status_from_title(title: str | None) -> MatchStatus | None:
        if not title:
            return None
        lower_title = title.lower()
        if 'ao vivo' in lower_title:
            return MatchStatus.LIVE
        if lower_title == 'preliminar':
            return MatchStatus.NOT_STARTED
        if 'colocar informa' in lower_title and 'online' in lower_title:
            return MatchStatus.NOT_STARTED
        return None

    @staticmethod
    def _extract_team_name(cell: Tag) -> str:
        link = cell.find('a')
        if link and isinstance(link, Tag):
            return link.get_text(strip=True)
        return ''

    @staticmethod
    def _extract_match_time(cell: Tag) -> str:
        live_indicator = cell.find('span', class_='green')
        if live_indicator and isinstance(live_indicator, Tag):
            text = live_indicator.get_text(strip=True)
            minute_match = MatchResultParser._minute_re.search(text)
            if minute_match:
                return f"{minute_match.group(1)}'"
        return ''

    @staticmethod
    def _extract_match_time_from_row(time_cell: Tag | None) -> str:
        if not time_cell:
            return ''
        live_indicator = time_cell.find('span', class_='live-ergebnis')
        if live_indicator and isinstance(live_indicator, Tag):
            text = live_indicator.get_text(strip=True)
            minute_match = MatchResultParser._minute_re.search(text)
            if minute_match:
                return f"{minute_match.group(1)}'"
        return ''
