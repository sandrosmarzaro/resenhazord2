"""Squad value HTML parsing for Transfermarkt."""

from bs4 import BeautifulSoup, Tag

from bot.domain.models.football import TmSquadStats
from bot.domain.services.transfermarkt.row_parser import RowParser


class SquadValueParser(RowParser):
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
