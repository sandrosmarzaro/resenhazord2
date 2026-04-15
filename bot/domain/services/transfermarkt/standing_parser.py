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
            tds = row.find_all('td')
            if not tds:
                continue
            rank_text = tds[0].get_text(strip=True).split()[0] if tds[0] else ''
            try:
                rank = int(rank_text)
            except ValueError:
                continue
            club_id = cls._first_href_match(row, '/verein/', cls._VEREIN_ID_RE)
            if club_id and club_id not in result:
                result[club_id] = rank
        return result

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
        rank_text = tds[0].get_text(strip=True).split()[0] if tds[0] else ''
        try:
            rank = int(rank_text)
        except ValueError:
            return None

        team = cls._extract_standing_team_name(row)
        if not team:
            return None

        cells = [
            td.get_text(strip=True)
            for td in row.find_all('td', class_='zentriert')
            if isinstance(td, Tag) and 'no-border-rechts' not in (td.get('class') or [])
        ]
        if len(cells) < cls._min_standing_cells:
            logger.warning('standing_row_too_few_cells', team=team, cells=len(cells))
            return None

        try:
            matches = int(cells[0])
            wins, draws, losses = int(cells[1]), int(cells[2]), int(cells[3])
            goals_for, goals_against = cls._parse_goals(cells[4])
            goal_diff = int(cells[5])
            points = int(cells[6])
        except (ValueError, IndexError):
            logger.warning('standing_row_parse_error', team=team)
            return None

        return TmStandingRow(
            rank=rank,
            team=team,
            matches=matches,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=goals_for,
            goals_against=goals_against,
            goal_diff=goal_diff,
            points=points,
        )

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
