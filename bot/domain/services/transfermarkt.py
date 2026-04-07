"""Transfermarkt scraper for most-valuable player rankings and squad values."""

import random
import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar

import structlog
from bs4 import BeautifulSoup, Tag

from bot.data.football import LeagueInfo
from bot.data.nationality_flags import nationality_flag
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

_BADGE_CDN = 'https://tmssl.akamaized.net/images/wappen/verysmall/{club_id}.png'
_TM_BASE = 'https://www.transfermarkt.com.br'
_CLUB_ID_RE = re.compile(r'/wappen/verysmall/(\d+)\.png')
_FOREIGNERS_RE = re.compile(r'(\d+)\s*\((\d+)%\)?')
_AGE_MIN = 15
_AGE_MAX = 45


@dataclass(frozen=True)
class TmPlayer:
    name: str
    position: str
    age: int
    nationality: str
    club: str
    club_id: str
    market_value: str
    photo_url: str
    badge_url: str
    profile_url: str = ''
    nationality_flag_url: str = ''
    nationality_flag_emoji: str = ''


@dataclass(frozen=True)
class TmClub:
    rank: int
    name: str
    country: str
    squad_value: str
    club_id: str
    badge_url: str


@dataclass(frozen=True)
class TmSquadStats:
    market_value: str
    squad_size: str
    avg_age: str
    foreigners_count: str
    foreigners_pct: str


def _extract_verein_name(row: Tag) -> str:
    """Extract club name from a table row, preferring /startseite/verein/ links with text."""
    for link in row.find_all('a', href=lambda h: bool(h and '/startseite/verein/' in str(h))):
        if not isinstance(link, Tag):
            continue
        text = link.get_text(strip=True)
        if text:
            return text
    name_tag = row.find('td', class_='hauptlink')
    if name_tag and isinstance(name_tag, Tag):
        return name_tag.get_text(strip=True)
    return ''


def _extract_money_td(row: Tag) -> str:
    """Extract the last td with class 'rechts' that contains a money string."""
    for td in reversed(row.find_all('td')):
        if not isinstance(td, Tag):
            continue
        classes = td.get('class') or []
        if isinstance(classes, list) and 'rechts' in classes:
            text = td.get_text(strip=True)
            if text and ('mi.' in text or 'mil.' in text or '€' in text):
                return text
    return ''


def _extract_badge_id(row: Tag) -> str:
    """Extract club_id from the first wappen img found in the row."""
    for img in row.find_all('img'):
        if not isinstance(img, Tag):
            continue
        src = str(img.get('src', '') or img.get('data-src', ''))
        m = _CLUB_ID_RE.search(src)
        if m:
            return m.group(1)
    return ''


def _extract_country(row: Tag) -> str:
    """Extract country name from a flaggenrahmen img title."""
    img = row.find('img', class_='flaggenrahmen')
    return str(img.get('title', '')) if img and isinstance(img, Tag) else ''


def _extract_squad_stats(row: Tag) -> tuple[str, str, str, str]:
    """Return (squad_size, avg_age, foreigners_count, foreigners_pct) from zentriert cells."""
    cells = [td for td in row.find_all('td', class_='zentriert') if isinstance(td, Tag)]
    integers: list[str] = []
    avg_age = ''
    foreigners_count = ''
    foreigners_pct = ''

    for td in cells:
        text = td.get_text(strip=True)
        if not text:
            continue
        m = _FOREIGNERS_RE.search(text)
        if m:
            foreigners_count = m.group(1)
            foreigners_pct = m.group(2)
            continue
        clean = text.replace(',', '.')
        try:
            val = float(clean)
            if ('.' in clean or ',' in text) and _AGE_MIN <= val <= _AGE_MAX:
                if not avg_age:
                    avg_age = text
            else:
                try:
                    int(text)
                    integers.append(text)
                except ValueError:
                    pass
        except ValueError:
            pass

    squad_size = integers[0] if integers else ''
    if not foreigners_count and len(integers) > 1:
        foreigners_count = integers[1]

    return squad_size, avg_age, foreigners_count, foreigners_pct


class TransfermarktService:
    GLOBAL_URL = (
        'https://www.transfermarkt.com.br/spieler-statistik/wertvollstespieler/marktwertetop'
    )
    CLUBS_URL = (
        'https://www.transfermarkt.com.br/spieler-statistik/wertvollstemannschaften/marktwertetop'
    )
    LEAGUE_URL = 'https://www.transfermarkt.com.br/{slug}/marktwerte/wettbewerb/{tm_id}/page/{page}'
    SQUAD_VALUES_URL = 'https://www.transfermarkt.com.br/{slug}/startseite/wettbewerb/{tm_id}'
    HEADERS: ClassVar[dict[str, str]] = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://www.transfermarkt.com.br/',
    }
    PLAYERS_PER_PAGE = 25
    GLOBAL_MAX_PAGES = 40  # top 1000 (40 x 25)
    LEAGUE_MAX_PAGES = 4
    POSITION_MAX_PAGES = 40

    # Maps Portuguese position text (as returned by transfermarkt.com.br) to formation role
    POSITION_ROLES: ClassVar[dict[str, str]] = {
        'Goleiro': 'GK',
        'Goalkeeper': 'GK',
        'Zagueiro': 'DEF',
        'Lateral Dir.': 'DEF',
        'Lateral Esq.': 'DEF',
        'Defensor Central': 'DEF',
        'Centre-Back': 'DEF',
        'Right-Back': 'DEF',
        'Left-Back': 'DEF',
        'Volante': 'MID',
        'Segundo Volante': 'MID',
        'Meia-Central': 'MID',
        'Meia Ofensivo': 'MID',
        'Meia Defensivo': 'MID',
        'Meia-Esquerda': 'MID',
        'Meia-Direita': 'MID',
        'Defensive Midfield': 'MID',
        'Central Midfield': 'MID',
        'Attacking Midfield': 'MID',
        'Right Midfield': 'MID',
        'Left Midfield': 'MID',
        'Centroavante': 'ATT',
        'Ponta Direita': 'ATT',
        'Ponta Esquerda': 'ATT',
        'Segundo Atacante': 'ATT',
        'Atacante de apoio': 'ATT',
        'Centre-Forward': 'ATT',
        'Right Winger': 'ATT',
        'Left Winger': 'ATT',
        'Second Striker': 'ATT',
    }

    # Transfermarkt position filter codes (kept for reference; pos= param ignored on .com.br)
    POSITION_CODES: ClassVar[dict[str, list[str]]] = {
        'GK': ['TW'],
        'DEF': ['IV', 'LV', 'RV'],
        'MID': ['DM', 'ZM', 'OM'],
        'ATT': ['LA', 'RA', 'MS'],
    }

    @classmethod
    async def fetch_squad_values(cls, league: LeagueInfo) -> dict[str, TmSquadStats]:
        """Return {club_name_lower: TmSquadStats} for all clubs in the league."""
        url = cls.SQUAD_VALUES_URL.format(slug=league.tm_slug, tm_id=league.tm_id)
        response = await HttpClient.get(url, headers=cls.HEADERS)
        response.raise_for_status()
        return cls._parse_squad_values(response.text)

    @staticmethod
    def _parse_squad_values(html: str) -> dict[str, TmSquadStats]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return {}
        result: dict[str, TmSquadStats] = {}
        for row in table.find_all('tr', class_=['odd', 'even']):
            if not isinstance(row, Tag):
                continue
            name = _extract_verein_name(row)
            if not name:
                continue
            value = _extract_money_td(row)
            squad_size, avg_age, foreigners_count, foreigners_pct = _extract_squad_stats(row)
            result[name.lower()] = TmSquadStats(
                market_value=value,
                squad_size=squad_size,
                avg_age=avg_age,
                foreigners_count=foreigners_count,
                foreigners_pct=foreigners_pct,
            )
        return result

    @classmethod
    async def fetch_top_clubs(cls, count: int) -> list[TmClub]:
        """Fetch the globally most-valuable clubs, up to *count* entries."""
        response = await HttpClient.get(cls.CLUBS_URL, headers=cls.HEADERS)
        response.raise_for_status()
        return cls._parse_clubs_page(response.text)[:count]

    @staticmethod
    def _parse_clubs_page(html: str) -> list[TmClub]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []
        clubs: list[TmClub] = []
        for rank, row in enumerate(table.find_all('tr', class_=['odd', 'even']), start=1):
            if not isinstance(row, Tag):
                continue
            name = _extract_verein_name(row)
            if not name:
                continue
            club_id = _extract_badge_id(row)
            clubs.append(
                TmClub(
                    rank=rank,
                    name=name,
                    country=_extract_country(row),
                    squad_value=_extract_money_td(row),
                    club_id=club_id,
                    badge_url=_BADGE_CDN.format(club_id=club_id) if club_id else '',
                )
            )
        return clubs

    @classmethod
    async def fetch_page(cls, page: int, league: LeagueInfo | None = None) -> list[TmPlayer]:
        if league:
            url = cls.LEAGUE_URL.format(slug=league.tm_slug, tm_id=league.tm_id, page=page)
        else:
            url = f'{cls.GLOBAL_URL}?page={page}'
        response = await HttpClient.get(url, headers=cls.HEADERS)
        response.raise_for_status()
        return cls._parse_page(response.text)

    @classmethod
    async def fetch_page_by_role(
        cls, role: str, page: int, league: LeagueInfo | None = None
    ) -> list[TmPlayer]:
        """Fetch a page of players filtered by formation role (GK/DEF/MID/ATT)."""
        codes = cls.POSITION_CODES.get(role, [])
        pos_code = random.choice(codes) if codes else ''  # noqa: S311
        if league:
            url = (
                cls.LEAGUE_URL.format(slug=league.tm_slug, tm_id=league.tm_id, page=page)
                + f'&pos={pos_code}'
            )
        else:
            url = f'{cls.GLOBAL_URL}?pos={pos_code}&page={page}'
        response = await HttpClient.get(url, headers=cls.HEADERS)
        response.raise_for_status()
        return cls._parse_page(response.text)

    @classmethod
    async def fetch_player_profile(cls, profile_url: str) -> dict[str, str]:
        """Fetch player profile page and return key stats (foot, height, other positions)."""
        response = await HttpClient.get(profile_url, headers=cls.HEADERS)
        response.raise_for_status()
        return cls._parse_player_profile(response.text)

    @staticmethod
    def _parse_player_profile(html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, 'html.parser')
        info: dict[str, str] = {}
        info_table = soup.find('div', class_='info-table')
        if not info_table or not isinstance(info_table, Tag):
            return info
        # Labels use --regular, values use --bold
        for label in info_table.find_all('span', class_='info-table__content--regular'):
            if not isinstance(label, Tag):
                continue
            key = label.get_text(strip=True).rstrip(':').strip()
            value_span = label.find_next_sibling('span', class_='info-table__content--bold')
            if value_span and isinstance(value_span, Tag):
                info[key] = value_span.get_text(strip=True).replace('\xa0', ' ')
        return info

    @staticmethod
    def _parse_page(html: str) -> list[TmPlayer]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []

        players: list[TmPlayer] = []
        for row in table.find_all('tr', class_=['odd', 'even']):
            if isinstance(row, Tag):
                player = TransfermarktService._parse_row(row)
                if player:
                    players.append(player)
        return players

    @staticmethod
    def _parse_row(row: Tag) -> TmPlayer | None:
        try:
            inline = row.find('table', class_='inline-table')
            if not inline or not isinstance(inline, Tag):
                return None

            photo_tag = inline.find('img', class_='bilderrahmen-fixed')
            if photo_tag and isinstance(photo_tag, Tag):
                src = photo_tag.get('data-src') or photo_tag.get('src', '')
                src_str = str(src)
                photo_url = (
                    '' if src_str.startswith('data:') else src_str.replace('/small/', '/big/')
                )
            else:
                photo_url = ''

            name_td = inline.find('td', class_='hauptlink')
            raw_name = (
                name_td.get_text(strip=True) if name_td and isinstance(name_td, Tag) else ''
            )
            name = unicodedata.normalize('NFC', raw_name)

            profile_url = ''
            if name_td and isinstance(name_td, Tag):
                name_link = name_td.find('a')
                if name_link and isinstance(name_link, Tag):
                    href = str(name_link.get('href', ''))
                    profile_url = f'{_TM_BASE}{href}' if href.startswith('/') else href

            trs = inline.find_all('tr')
            if len(trs) > 1 and isinstance(trs[1], Tag):
                pos_td = trs[1].find('td')
                position = pos_td.get_text(strip=True) if pos_td and isinstance(pos_td, Tag) else ''
            else:
                position = ''

            cells = row.find_all('td', class_='zentriert')
            age_text = next(
                (
                    c.get_text(strip=True)
                    for c in cells
                    if isinstance(c, Tag)
                    and c.get_text(strip=True).isdigit()
                    and _AGE_MIN <= int(c.get_text(strip=True)) <= _AGE_MAX
                ),
                '0',
            )
            age = int(age_text)

            nat_tag = row.find('img', class_='flaggenrahmen')
            nationality = (
                str(nat_tag.get('title', '')) if nat_tag and isinstance(nat_tag, Tag) else ''
            )
            nationality_flag_url = (
                str(nat_tag.get('src') or nat_tag.get('data-src') or '')
                if nat_tag and isinstance(nat_tag, Tag)
                else ''
            )

            club_link = row.find('a', href=lambda h: bool(h and '/startseite/verein/' in str(h)))
            club = (
                str(club_link.get('title', '')) if club_link and isinstance(club_link, Tag) else ''
            )

            club_img = club_link.find('img') if club_link and isinstance(club_link, Tag) else None
            if club_img and isinstance(club_img, Tag):
                src_val = str(club_img.get('src', ''))
                club_id_match = _CLUB_ID_RE.search(src_val)
            else:
                club_id_match = None
            club_id = club_id_match.group(1) if club_id_match else ''
            badge_url = _BADGE_CDN.format(club_id=club_id) if club_id else ''

            value_tag = row.find(
                'td', class_=lambda c: bool(c and 'rechts' in c and 'hauptlink' in c)
            )
            market_value = (
                value_tag.get_text(strip=True) if value_tag and isinstance(value_tag, Tag) else ''
            )

            if not name or not club:
                return None

            return TmPlayer(
                name=name,
                position=position,
                age=age,
                nationality=nationality,
                club=club,
                club_id=club_id,
                market_value=market_value,
                photo_url=photo_url,
                badge_url=badge_url,
                profile_url=profile_url,
                nationality_flag_url=nationality_flag_url,
                nationality_flag_emoji=nationality_flag(nationality),
            )
        except Exception:
            logger.exception('transfermarkt_parse_row_error')
            return None
