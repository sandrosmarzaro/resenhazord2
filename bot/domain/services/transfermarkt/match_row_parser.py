"""Row parsing for live matches."""

from dataclasses import dataclass

from bs4 import Tag

from bot.domain.models.football import TmLiveMatch
from bot.domain.services.transfermarkt.match_result_parser import MatchResultParser


@dataclass(frozen=True)
class CompetitionContext:
    name: str
    code: str
    country: str
    flag_emoji: str


class MatchRowParser:
    @classmethod
    def parse_live_table_rows(cls, table: Tag, comp_ctx: CompetitionContext) -> list[TmLiveMatch]:
        matches: list[TmLiveMatch] = []

        for row in table.find_all('tr'):
            if not isinstance(row, Tag):
                continue

            home_cell = row.find('td', class_='verein-heim')
            away_cell = row.find('td', class_='verein-gast')
            result_cell = row.find('td', class_='ergebnis')
            time_cell = row.find('td', class_='zeit')

            if not (home_cell and away_cell and result_cell):
                continue

            home_team = MatchResultParser._extract_team_name(home_cell)
            away_team = MatchResultParser._extract_team_name(away_cell)

            result_link = result_cell.find('a')
            if not result_link or not isinstance(result_link, Tag):
                continue

            match_id = MatchResultParser._extract_match_id(result_link)
            home_score, away_score, status, match_time = MatchResultParser.parse_match_result(
                result_link, result_cell, time_cell
            )

            round_span = row.find('span', class_=' Spieltag')
            round_str = (
                round_span.get_text(strip=True)
                if round_span and isinstance(round_span, Tag)
                else None
            )

            matches.append(
                TmLiveMatch(
                    competition_code=comp_ctx.code,
                    competition_name=comp_ctx.name,
                    country=comp_ctx.country,
                    country_flag_emoji=comp_ctx.flag_emoji,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    match_time=match_time,
                    status=status,
                    match_id=match_id,
                    round=round_str,
                )
            )

        return matches
