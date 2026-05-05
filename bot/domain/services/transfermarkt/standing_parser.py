"""Standing HTML parsing for Transfermarkt."""

from typing import ClassVar

import structlog
from bs4 import BeautifulSoup, Tag

from bot.domain.models.football import TmStandingRow
from bot.domain.services.transfermarkt.row_parser import RowParser

logger = structlog.get_logger()


class StandingParser(RowParser):
    _min_standing_cells: ClassVar[int] = 7
    _goals_separator: ClassVar[str] = ':'

    @classmethod
    def parse_tabelle(cls, html: str) -> dict[str, int]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return {}
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if isinstance(tbody, Tag) else table.find_all('tr')
        result: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, Tag):
                continue
            entry = cls._parse_rank_entry(row)
            if entry:
                club_id, rank = entry
                if club_id not in result:
                    result[club_id] = rank
        return result

    @classmethod
    def _parse_rank_entry(cls, row: Tag) -> tuple[str, int] | None:
        tds = row.find_all('td')
        if not tds:
            return None
        rank_text = tds[0].get_text(strip=True).split()[0] if tds[0] else ''
        try:
            rank = int(rank_text)
        except ValueError:
            return None
        club_id = cls._first_href_match(row, '/verein/', cls._VEREIN_ID_RE)
        if not club_id:
            return None
        return club_id, rank

    @classmethod
    def parse_full_tabelle(cls, html: str) -> list[TmStandingRow]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if isinstance(tbody, Tag) else table.find_all('tr')
        result: list[TmStandingRow] = []
        for row in rows:
            if not isinstance(row, Tag):
                continue
            standing = cls._parse_standing_row(row)
            if standing:
                result.append(standing)
        return result

    @classmethod
    def _parse_standing_row(cls, row: Tag) -> TmStandingRow | None:
        tds = row.find_all('td')
        if not tds:
            return None
        rank = cls._parse_rank(tds[0])
        if rank is None:
            return None

        team = cls._extract_standing_team_name(row)
        if not team:
            return None

        cells = cls._extract_centered_cells(row)
        if len(cells) < cls._min_standing_cells:
            logger.warning('standing_row_too_few_cells', team=team, cells=len(cells))
            return None

        values = cls._parse_standing_values(cells, team)
        if values is None:
            return None

        return TmStandingRow(rank=rank, team=team, **values)

    @classmethod
    def _parse_rank(cls, td: Tag) -> int | None:
        rank_text = td.get_text(strip=True).split()[0] if td else ''
        try:
            return int(rank_text)
        except ValueError:
            return None

    @classmethod
    def _extract_centered_cells(cls, row: Tag) -> list[str]:
        return [
            td.get_text(strip=True)
            for td in row.find_all('td', class_='zentriert')
            if isinstance(td, Tag) and 'no-border-rechts' not in (td.get('class') or [])
        ]

    @classmethod
    def _parse_standing_values(cls, cells: list[str], team: str) -> dict | None:
        try:
            goals_for, goals_against = cls._parse_goals(cells[4])
            return {
                'matches': int(cells[0]),
                'wins': int(cells[1]),
                'draws': int(cells[2]),
                'losses': int(cells[3]),
                'goals_for': goals_for,
                'goals_against': goals_against,
                'goal_diff': int(cells[5]),
                'points': int(cells[6]),
            }
        except (ValueError, IndexError):
            logger.warning('standing_row_parse_error', team=team)
            return None

    @classmethod
    def _parse_goals(cls, text: str) -> tuple[int, int]:
        parts = text.split(cls._goals_separator)
        return int(parts[0]), int(parts[1])

    @staticmethod
    def _extract_standing_team_name(row: Tag) -> str:
        td = row.find('td', class_='no-border-links')
        if td and isinstance(td, Tag):
            link = td.find('a')
            if link and isinstance(link, Tag):
                return link.get_text(strip=True)
        return ''
