"""HTML parsing for Transfermarkt pages — public facade."""

import re

import structlog
from bs4 import BeautifulSoup, Tag

from bot.data.nationality_flags import nationality_flag
from bot.data.transfermarkt_country_codes import (
    COMPETITION_CODE_OVERRIDES,
    COUNTRY_CODE_TO_FLAG,
)
from bot.domain.models.football import (
    MatchStatus,
    TmClub,
    TmLiveMatch,
    TmPlayer,
    TmSquadStats,
    TmStandingRow,
)
from bot.domain.services.transfermarkt.parse_helpers import ParseHelpers
from bot.domain.services.transfermarkt.row_parser import RowParser

logger = structlog.get_logger()

_GOALS_SEPARATOR = ':'
_MIN_STANDING_CELLS = 7
_SCORE_PARTS_COUNT = 2
_TIME_FORMAT_LENGTH = 5
_MAJOR_COMP_CODE_LENGTH = 2
_MAX_HOUR = 23
_MAX_MINUTE = 59


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
            comp_info = cls._extract_competition_info_from_live_block(block)
            if not comp_info:
                continue
            comp_name, comp_code, country, country_flag = comp_info
            table = block.find('table', class_='livescore')
            if not table or not isinstance(table, Tag):
                continue
            for match in cls._parse_live_table_rows(
                table, comp_code, comp_name, country, country_flag
            ):
                if match.match_id not in seen_match_ids:
                    seen_match_ids.add(match.match_id)
                    matches.append(match)

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
                comp_info = cls._extract_competition_info_from_kategorie(kategorie)
                if not comp_info:
                    continue
                comp_name, comp_code, country, country_flag = comp_info
                table = cls._find_livescore_table_for_kategorie(kategorie)
                if not table or not isinstance(table, Tag):
                    continue
                for match in cls._parse_live_table_rows(
                    table, comp_code, comp_name, country, country_flag
                ):
                    if match.match_id not in seen_match_ids:
                        seen_match_ids.add(match.match_id)
                        matches.append(match)

        return matches

    @classmethod
    def _extract_competition_info_from_kategorie(
        cls, kategorie: Tag
    ) -> tuple[str, str, str, str] | None:
        header = kategorie.find('h2')
        if not header or not isinstance(header, Tag):
            return None

        comp_link = header.find('a')
        comp_name = ''
        comp_href = ''
        if comp_link and isinstance(comp_link, Tag):
            comp_name = comp_link.get_text(strip=True)
            comp_href = comp_link.get('href', '')

        comp_code = ''
        if comp_href:
            match = cls._WETTBEWERB_ID_RE.search(str(comp_href))
            if not match:
                match = ParseHelpers._WETTBEWERB_ID_RE_V2.search(str(comp_href))
            if match:
                comp_code = match.group(1)

        flag_img = kategorie.find('img', class_='wettbewerblogo')
        country = ''
        if flag_img and isinstance(flag_img, Tag):
            title = str(flag_img.get('title', ''))
            if title and title != comp_name:
                country = title

        country_flag = cls._get_country_flag(comp_code, country)

        return comp_name, comp_code, country, country_flag

    @staticmethod
    def _get_country_flag(comp_code: str, country_name: str) -> str:
        if comp_code:
            code = comp_code.split('/', maxsplit=1)[0]
            override = COMPETITION_CODE_OVERRIDES.get(code)
            if override:
                return override
        if country_name:
            flag = nationality_flag(country_name)
            if flag:
                return flag
        if comp_code:
            code = comp_code.split('/', maxsplit=1)[0]
            for length in (3, 2):
                if len(code) >= length:
                    flag = COUNTRY_CODE_TO_FLAG.get(code[:length])
                    if flag:
                        return flag
        return ''

    @classmethod
    def _extract_competition_info_from_live_block(
        cls, block: Tag
    ) -> tuple[str, str, str, str] | None:
        header = block.find('h2')
        if not header or not isinstance(header, Tag):
            return None

        comp_link = header.find('a')
        comp_name = ''
        comp_href = ''
        if comp_link and isinstance(comp_link, Tag):
            comp_name = comp_link.get_text(strip=True)
            comp_href = comp_link.get('href', '')

        comp_code = ''
        if comp_href:
            match = cls._WETTBEWERB_ID_RE.search(str(comp_href))
            if not match:
                match = ParseHelpers._WETTBEWERB_ID_RE_V2.search(str(comp_href))
            if match:
                comp_code = match.group(1)

        flag_img = header.find('img', class_='wettbewerblogo')
        country = ''
        if flag_img and isinstance(flag_img, Tag):
            title = str(flag_img.get('title', ''))
            if title and title != comp_name:
                country = title

        country_flag = cls._get_country_flag(comp_code, country)

        return comp_name, comp_code, country, country_flag

    @classmethod
    def _find_livescore_table_for_kategorie(cls, kategorie: Tag) -> Tag | None:
        siblings = kategorie.find_next_siblings()
        for sibling in siblings:
            if not isinstance(sibling, Tag):
                continue
            if sibling.name == 'table' and 'livescore' in sibling.get('class', []):
                return sibling
            if sibling.name == 'div' and 'kategorie' in sibling.get('class', []):
                break
        return None

    @classmethod
    def _parse_live_table_rows(
        cls, table: Tag, comp_code: str, comp_name: str, country: str, country_flag: str
    ) -> list[TmLiveMatch]:
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

            home_team = cls._extract_team_name(home_cell)
            away_team = cls._extract_team_name(away_cell)

            result_link = result_cell.find('a')
            if not result_link or not isinstance(result_link, Tag):
                continue

            match_id = cls._extract_match_id(result_link)

            parsed_result = cls._parse_match_result(result_link, result_cell, time_cell)
            home_score, away_score, status, match_time = parsed_result

            round_span = row.find('span', class_=' Spieltag')
            round_str = (
                round_span.get_text(strip=True)
                if round_span and isinstance(round_span, Tag)
                else None
            )

            matches.append(
                TmLiveMatch(
                    competition_code=comp_code,
                    competition_name=comp_name,
                    country=country,
                    country_flag_emoji=country_flag,
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

    @classmethod
    def _parse_match_result(
        cls, result_link: Tag, result_cell: Tag, time_cell: Tag | None = None
    ) -> tuple[int | None, int | None, MatchStatus, str]:
        result_text = cls._extract_result_text(result_link)
        title = result_link.get('title', '')
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

    @staticmethod
    def _is_finished_result(result_link: Tag) -> bool:
        span = result_link.find('span', class_='matchresult')
        if not span or not isinstance(span, Tag):
            return False
        return 'finished' in (span.get('class') or [])

    @classmethod
    def _parse_score_parts(cls, result_text: str) -> tuple[int | None, int | None]:
        separator = ' - ' if ' - ' in result_text else ':'
        parts = result_text.split(separator)
        if len(parts) != _SCORE_PARTS_COUNT:
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
        if len(parts) != _SCORE_PARTS_COUNT:
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
            mid_match = re.search(r'/spielbericht/(\d+)', str(match_id_href))
            if mid_match:
                return mid_match.group(1)
            mid_match = re.search(r'/ticker/begegnung/live/(\d+)', str(match_id_href))
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
        if len(result_text) == _TIME_FORMAT_LENGTH and result_text[2] == ':':
            return False
        if ':' in result_text:
            parts = result_text.split(':')
            if len(parts) == _SCORE_PARTS_COUNT and parts[0].isdigit() and parts[1].isdigit():
                return True
        return ' - ' in result_text

    @staticmethod
    def _looks_like_scheduled_time(text: str) -> bool:
        if not text or len(text) != _TIME_FORMAT_LENGTH or text[2] != ':':
            return False
        try:
            hour, minute = text.split(':')
            hour_int, minute_int = int(hour), int(minute)
        except ValueError:
            return False
        return 0 <= hour_int <= _MAX_HOUR and 0 <= minute_int <= _MAX_MINUTE

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
            minute_match = re.search(r'(\d+)', text)
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
            minute_match = re.search(r'(\d+)', text)
            if minute_match:
                return f"{minute_match.group(1)}'"
        return ''
