"""Live-match HTML parsing for Transfermarkt."""

from bs4 import BeautifulSoup, Tag

from bot.domain.models.football import TmLiveMatch
from bot.domain.services.transfermarkt.competition_parser import CompetitionParser
from bot.domain.services.transfermarkt.match_row_parser import CompetitionContext, MatchRowParser


class LiveMatchParser:
    @classmethod
    def parse_live_matches(cls, html: str) -> list[TmLiveMatch]:
        soup = BeautifulSoup(html, 'html.parser')
        matches: list[TmLiveMatch] = []
        seen_match_ids: set[str] = set()

        cls._parse_live_block_section(soup, matches, seen_match_ids)
        cls._parse_box_section(soup, matches, seen_match_ids)

        return matches

    @classmethod
    def _parse_live_block_section(
        cls, soup: BeautifulSoup, matches: list[TmLiveMatch], seen_match_ids: set[str]
    ) -> None:
        for block in soup.find_all('div', class_='live-block'):
            if not isinstance(block, Tag):
                continue
            header = block.find('h2')
            if not header or not isinstance(header, Tag):
                continue
            comp_ctx = CompetitionParser.build_competition_context(header, flag_search_in=header)
            if not comp_ctx:
                continue
            table = block.find('table', class_='livescore')
            if not table or not isinstance(table, Tag):
                continue
            cls._collect_matches(table, comp_ctx, matches, seen_match_ids)

    @classmethod
    def _parse_box_section(
        cls, soup: BeautifulSoup, matches: list[TmLiveMatch], seen_match_ids: set[str]
    ) -> None:
        for box in soup.find_all('div', class_='box'):
            if not isinstance(box, Tag):
                continue
            for kategorie in box.find_all('div', class_='kategorie'):
                if not isinstance(kategorie, Tag):
                    continue
                cls._parse_kategorie(kategorie, matches, seen_match_ids)

    @classmethod
    def _parse_kategorie(
        cls, kategorie: Tag, matches: list[TmLiveMatch], seen_match_ids: set[str]
    ) -> None:
        header = kategorie.find('h2')
        if not header or not isinstance(header, Tag):
            return
        comp_ctx = CompetitionParser.build_competition_context(header, flag_search_in=kategorie)
        if not comp_ctx:
            return
        table = CompetitionParser.find_livescore_table_for_kategorie(kategorie)
        if not table or not isinstance(table, Tag):
            return
        cls._collect_matches(table, comp_ctx, matches, seen_match_ids)

    @classmethod
    def _collect_matches(
        cls,
        table: Tag,
        comp_ctx: CompetitionContext,
        matches: list[TmLiveMatch],
        seen_match_ids: set[str],
    ) -> None:
        for match in MatchRowParser.parse_live_table_rows(table, comp_ctx):
            if match.match_id not in seen_match_ids:
                seen_match_ids.add(match.match_id)
                matches.append(match)
