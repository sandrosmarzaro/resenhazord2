"""Club HTML parsing for Transfermarkt."""

from bs4 import BeautifulSoup, Tag

from bot.domain.models.football import TmClub
from bot.domain.services.transfermarkt.row_parser import RowParser


class ClubParser(RowParser):
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
