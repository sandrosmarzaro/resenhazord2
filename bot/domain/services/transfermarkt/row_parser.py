"""Row-level and profile parsing for Transfermarkt HTML."""

import unicodedata

import structlog
from bs4 import BeautifulSoup, Tag

from bot.data.nationality_flags import nationality_flag
from bot.domain.models.football import TmPlayer
from bot.domain.services.transfermarkt.parse_helpers import ParseHelpers

logger = structlog.get_logger()


class RowParser(ParseHelpers):
    @classmethod
    def parse_player_profile(cls, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, 'html.parser')
        info: dict[str, str] = {}
        cls._parse_info_table(soup, info)
        cls._parse_detail_position(soup, info)
        return info

    @classmethod
    def _parse_info_table(cls, soup: BeautifulSoup, info: dict[str, str]) -> None:
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
            if key in cls._BIRTH_PLACE_KEYS:
                flag_img = value_span.find('img', class_='flaggenrahmen')
                if flag_img and isinstance(flag_img, Tag):
                    country = str(flag_img.get('title', ''))
                    if country:
                        info['País de nascimento'] = country

    @staticmethod
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

    @classmethod
    def _parse_row(cls, row: Tag, *, require_club: bool = True) -> TmPlayer | None:
        try:
            inline = row.find('table', class_='inline-table')
            if not inline or not isinstance(inline, Tag):
                return None

            photo_url = cls._extract_photo_url(inline)

            name_td = inline.find('td', class_='hauptlink')
            raw_name = name_td.get_text(strip=True) if name_td and isinstance(name_td, Tag) else ''
            name = unicodedata.normalize('NFC', raw_name)

            profile_url = ''
            if name_td and isinstance(name_td, Tag):
                name_link = name_td.find('a')
                if name_link and isinstance(name_link, Tag):
                    href = str(name_link.get('href', ''))
                    profile_url = f'{cls.TM_BASE}{href}' if href.startswith('/') else href

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
                    and cls._AGE_MIN <= int(c.get_text(strip=True)) <= cls._AGE_MAX
                ),
                '0',
            )
            age = int(age_text)

            nat_tag = row.find('img', class_='flaggenrahmen')
            if nat_tag and isinstance(nat_tag, Tag):
                nationality = str(nat_tag.get('title', ''))
                nationality_flag_url = str(nat_tag.get('src') or nat_tag.get('data-src') or '')
            else:
                nationality = ''
                nationality_flag_url = ''

            club_link = row.find('a', href=lambda h: bool(h and '/startseite/verein/' in str(h)))
            club = (
                str(club_link.get('title', '')) if club_link and isinstance(club_link, Tag) else ''
            )

            club_img = club_link.find('img') if club_link and isinstance(club_link, Tag) else None
            if club_img and isinstance(club_img, Tag):
                src_val = str(club_img.get('src', ''))
                club_id_match = cls._CLUB_ID_RE.search(src_val)
            else:
                club_id_match = None
            club_id = club_id_match.group(1) if club_id_match else ''
            badge_url = cls.BADGE_CDN.format(club_id=club_id) if club_id else ''

            value_tag = row.find(
                'td', class_=lambda c: bool(c and 'rechts' in c and 'hauptlink' in c)
            )
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
