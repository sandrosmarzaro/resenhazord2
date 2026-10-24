"""Standing HTML parsing for Transfermarkt."""

from bs4 import BeautifulSoup, Tag

from bot.domain.services.transfermarkt.row_parser import RowParser


class StandingParser(RowParser):
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
