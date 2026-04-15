"""Player HTML parsing for Transfermarkt."""

from bs4 import BeautifulSoup, Tag

from bot.domain.models.football import TmPlayer
from bot.domain.services.transfermarkt.row_parser import RowParser


class PlayerParser(RowParser):
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
