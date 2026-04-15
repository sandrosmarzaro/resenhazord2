"""HTML parsing for Transfermarkt pages — public facade."""

import structlog
from bs4 import BeautifulSoup, Tag

from bot.domain.models.football import (
    TmClub,
    TmLiveMatch,
    TmPlayer,
    TmSquadStats,
    TmStandingRow,
)
from bot.domain.services.transfermarkt.live_parser import LiveMatchParser
from bot.domain.services.transfermarkt.row_parser import RowParser

logger = structlog.get_logger()

_GOALS_SEPARATOR = ':'
_MIN_STANDING_CELLS = 7


class TransfermarktParser(RowParser):
    @classmethod
    def parse_page(cls, html: str, *, require_club: bool = True) -> list[TmPlayer]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []

        players: list[TmPlayer] = []
        for row in table.find_all('tr', class_=['odd', 'even']):
            if isinstance(row, Tag):
                player = cls._parse_row(row, require_club=require_club)
                if player:
                    players.append(player)
        return players

    @classmethod
    def parse_squad_values(cls, html: str) -> dict[str, TmSquadStats]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return {}
        result: dict[str, TmSquadStats] = {}
        for row in table.find_all('tr', class_=['odd', 'even']):
            if not isinstance(row, Tag):
                continue
            name = cls._extract_verein_name(row)
            if not name:
                continue
            club_id = cls._first_href_match(row, '/startseite/verein/', cls._VEREIN_ID_RE)
            if not club_id:
                continue
            value = cls._extract_money_td(row)
            squad_size, avg_age, foreigners_count, foreigners_pct = cls._extract_squad_stats(row)
            result[club_id] = TmSquadStats(
                market_value=value,
                squad_size=squad_size,
                avg_age=avg_age,
                foreigners_count=foreigners_count,
                foreigners_pct=foreigners_pct,
                club_id=club_id,
                name=name,
                badge_url=cls.BADGE_CDN.format(club_id=club_id),
            )
        return result

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
        if len(cells) < _MIN_STANDING_CELLS:
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

    @staticmethod
    def _parse_goals(text: str) -> tuple[int, int]:
        parts = text.split(_GOALS_SEPARATOR)
        return int(parts[0]), int(parts[1])

    @staticmethod
    def _extract_standing_team_name(row: Tag) -> str:
        td = row.find('td', class_='no-border-links')
        if td and isinstance(td, Tag):
            link = td.find('a')
            if link and isinstance(link, Tag):
                return link.get_text(strip=True)
        return ''

    @classmethod
    def parse_clubs_page(cls, html: str) -> list[TmClub]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []
        clubs: list[TmClub] = []
        for rank, row in enumerate(table.find_all('tr', class_=['odd', 'even']), start=1):
            if not isinstance(row, Tag):
                continue
            name = cls._extract_verein_name(row)
            if not name:
                continue
            club_id = cls._first_href_match(row, '/startseite/verein/', cls._VEREIN_ID_RE)
            league_tm_id = cls._first_href_match(row, '/wettbewerb/', cls._WETTBEWERB_ID_RE)
            clubs.append(
                TmClub(
                    rank=rank,
                    name=name,
                    country=cls._extract_country(row),
                    squad_value=cls._extract_money_td(row),
                    club_id=club_id,
                    badge_url=cls.BADGE_CDN.format(club_id=club_id) if club_id else '',
                    league_tm_id=league_tm_id,
                )
            )
        return clubs

    @classmethod
    def parse_league_clubs(cls, html: str) -> list[TmClub]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []
        clubs: list[TmClub] = []
        seen: set[str] = set()
        for row in table.find_all('tr', class_=['odd', 'even']):
            if not isinstance(row, Tag):
                continue
            name = cls._extract_verein_name(row)
            if not name:
                continue
            club_id = cls._first_href_match(row, '/startseite/verein/', cls._VEREIN_ID_RE)
            if not club_id or club_id in seen:
                continue
            seen.add(club_id)
            clubs.append(
                TmClub(
                    rank=len(clubs) + 1,
                    name=name,
                    country='',
                    squad_value=cls._extract_money_td(row),
                    club_id=club_id,
                    badge_url=cls.BADGE_CDN.format(club_id=club_id),
                )
            )
        return clubs

    @classmethod
    def parse_live_matches(cls, html: str) -> list[TmLiveMatch]:
        return LiveMatchParser.parse_live_matches(html)

