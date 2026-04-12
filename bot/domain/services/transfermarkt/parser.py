"""HTML parsing for Transfermarkt pages — pure functions, no HTTP calls."""

import re
import unicodedata

import structlog
from bs4 import BeautifulSoup, Tag

from bot.data.nationality_flags import nationality_flag
from bot.domain.models.football import TmClub, TmPlayer, TmSquadStats

logger = structlog.get_logger()

_BADGE_CDN = 'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png'
_TM_BASE = 'https://www.transfermarkt.com.br'
_CLUB_ID_RE = re.compile(r'/wappen/verysmall/(\d+)\.png')
_PORTRAIT_SIZE_RE = re.compile(r'/portrait/(?:small|medium|header)/')
_VEREIN_ID_RE = re.compile(r'/verein/(\d+)')
_WETTBEWERB_ID_RE = re.compile(r'/wettbewerb/([A-Z0-9]+)(?:$|[/?])')
_FOREIGNERS_RE = re.compile(r'(\d+)\s*\((\d+)%\)?')
_VALUE_RE = re.compile(r'€\s*([\d.,]+)\s*(mi\.|mil\.)')
_AGE_MIN = 15
_AGE_MAX = 45
_BIRTH_PLACE_KEYS = {'Local de nascimento', 'Place of birth'}


class TransfermarktParser:
    VALUE_RE = _VALUE_RE
    TM_BASE = _TM_BASE
    BADGE_CDN = _BADGE_CDN

    @staticmethod
    def parse_page(html: str, *, require_club: bool = True) -> list[TmPlayer]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []

        players: list[TmPlayer] = []
        for row in table.find_all('tr', class_=['odd', 'even']):
            if isinstance(row, Tag):
                player = _parse_row(row, require_club=require_club)
                if player:
                    players.append(player)
        return players

    @staticmethod
    def parse_squad_values(html: str) -> dict[str, TmSquadStats]:
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
            club_id = _first_href_match(row, '/startseite/verein/', _VEREIN_ID_RE)
            if not club_id:
                continue
            value = _extract_money_td(row)
            squad_size, avg_age, foreigners_count, foreigners_pct = _extract_squad_stats(row)
            result[club_id] = TmSquadStats(
                market_value=value,
                squad_size=squad_size,
                avg_age=avg_age,
                foreigners_count=foreigners_count,
                foreigners_pct=foreigners_pct,
                club_id=club_id,
                name=name,
                badge_url=_BADGE_CDN.format(club_id=club_id),
            )
        return result

    @staticmethod
    def parse_tabelle(html: str) -> dict[str, int]:
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
            club_id = _first_href_match(row, '/verein/', _VEREIN_ID_RE)
            if club_id and club_id not in result:
                result[club_id] = rank
        return result

    @staticmethod
    def parse_clubs_page(html: str) -> list[TmClub]:
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
            club_id = _first_href_match(row, '/startseite/verein/', _VEREIN_ID_RE)
            league_tm_id = _first_href_match(row, '/wettbewerb/', _WETTBEWERB_ID_RE)
            clubs.append(
                TmClub(
                    rank=rank,
                    name=name,
                    country=_extract_country(row),
                    squad_value=_extract_money_td(row),
                    club_id=club_id,
                    badge_url=_BADGE_CDN.format(club_id=club_id) if club_id else '',
                    league_tm_id=league_tm_id,
                )
            )
        return clubs

    @staticmethod
    def parse_player_profile(html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, 'html.parser')
        info: dict[str, str] = {}
        _parse_info_table(soup, info)
        _parse_detail_position(soup, info)
        return info

    @staticmethod
    def parse_league_clubs(html: str) -> list[TmClub]:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='items')
        if not table or not isinstance(table, Tag):
            return []
        clubs: list[TmClub] = []
        seen: set[str] = set()
        for row in table.find_all('tr', class_=['odd', 'even']):
            if not isinstance(row, Tag):
                continue
            name = _extract_verein_name(row)
            if not name:
                continue
            club_id = _first_href_match(row, '/startseite/verein/', _VEREIN_ID_RE)
            if not club_id or club_id in seen:
                continue
            seen.add(club_id)
            clubs.append(
                TmClub(
                    rank=len(clubs) + 1,
                    name=name,
                    country='',
                    squad_value=_extract_money_td(row),
                    club_id=club_id,
                    badge_url=_BADGE_CDN.format(club_id=club_id),
                )
            )
        return clubs


def _extract_photo_url(inline: Tag) -> str:
    photo_tag = inline.find('img', class_='bilderrahmen-fixed')
    if not photo_tag or not isinstance(photo_tag, Tag):
        return ''
    src = photo_tag.get('data-src') or photo_tag.get('src', '')
    src_str = str(src)
    if src_str.startswith('data:'):
        return ''
    return _PORTRAIT_SIZE_RE.sub('/portrait/big/', src_str)


def _extract_verein_name(row: Tag) -> str:
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
    for img in row.find_all('img'):
        if not isinstance(img, Tag):
            continue
        src = str(img.get('src', '') or img.get('data-src', ''))
        m = _CLUB_ID_RE.search(src)
        if m:
            return m.group(1)
    return ''


def _extract_country(row: Tag) -> str:
    img = row.find('img', class_='flaggenrahmen')
    return str(img.get('title', '')) if img and isinstance(img, Tag) else ''


def _first_href_match(row: Tag, fragment: str, pattern: re.Pattern[str]) -> str:
    for link in row.find_all('a', href=lambda h: bool(h and fragment in str(h))):
        if not isinstance(link, Tag):
            continue
        m = pattern.search(str(link.get('href', '')))
        if m:
            return m.group(1)
    return ''


def _extract_squad_stats(row: Tag) -> tuple[str, str, str, str]:
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


def _parse_info_table(soup: BeautifulSoup, info: dict[str, str]) -> None:
    info_table = soup.find('div', class_='info-table')
    if not info_table or not isinstance(info_table, Tag):
        return
    for label in info_table.find_all('span', class_='info-table__content--regular'):
        if not isinstance(label, Tag):
            continue
        key = label.get_text(strip=True).rstrip(':').strip()
        value_span = label.find_next_sibling('span', class_='info-table__content--bold')
        if not value_span or not isinstance(value_span, Tag):
            continue
        info[key] = value_span.get_text(strip=True).replace('\xa0', ' ')
        if key in _BIRTH_PLACE_KEYS:
            flag_img = value_span.find('img', class_='flaggenrahmen')
            if flag_img and isinstance(flag_img, Tag):
                country = str(flag_img.get('title', ''))
                if country:
                    info['País de nascimento'] = country


def _parse_detail_position(soup: BeautifulSoup, info: dict[str, str]) -> None:
    detail = soup.find('div', class_='detail-position')
    if not detail or not isinstance(detail, Tag):
        return
    dts = detail.find_all('dt')
    dds = detail.find_all('dd')
    for dt, dd in zip(dts, dds, strict=False):
        if not isinstance(dt, Tag) or not isinstance(dd, Tag):
            continue
        key = dt.get_text(strip=True).rstrip(':').strip()
        value = dd.get_text(' ', strip=True)
        if key and value:
            info[key] = value


def _parse_row(row: Tag, *, require_club: bool = True) -> TmPlayer | None:
    try:
        inline = row.find('table', class_='inline-table')
        if not inline or not isinstance(inline, Tag):
            return None

        photo_url = _extract_photo_url(inline)

        name_td = inline.find('td', class_='hauptlink')
        raw_name = name_td.get_text(strip=True) if name_td and isinstance(name_td, Tag) else ''
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
        nationality = str(nat_tag.get('title', '')) if nat_tag and isinstance(nat_tag, Tag) else ''
        nationality_flag_url = (
            str(nat_tag.get('src') or nat_tag.get('data-src') or '')
            if nat_tag and isinstance(nat_tag, Tag)
            else ''
        )

        club_link = row.find('a', href=lambda h: bool(h and '/startseite/verein/' in str(h)))
        club = str(club_link.get('title', '')) if club_link and isinstance(club_link, Tag) else ''

        club_img = club_link.find('img') if club_link and isinstance(club_link, Tag) else None
        if club_img and isinstance(club_img, Tag):
            src_val = str(club_img.get('src', ''))
            club_id_match = _CLUB_ID_RE.search(src_val)
        else:
            club_id_match = None
        club_id = club_id_match.group(1) if club_id_match else ''
        badge_url = _BADGE_CDN.format(club_id=club_id) if club_id else ''

        value_tag = row.find('td', class_=lambda c: bool(c and 'rechts' in c and 'hauptlink' in c))
        market_value = (
            value_tag.get_text(strip=True) if value_tag and isinstance(value_tag, Tag) else ''
        )

        if not name:
            return None
        if require_club and not club:
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
