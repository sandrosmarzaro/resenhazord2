"""Shared extraction helpers and constants for Transfermarkt HTML parsing."""

import re

from bs4 import Tag


class ParseHelpers:
    BADGE_CDN = 'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png'
    TM_BASE = 'https://www.transfermarkt.com.br'

    _CLUB_ID_RE = re.compile(r'/wappen/verysmall/(\d+)\.png')
    _PORTRAIT_SIZE_RE = re.compile(r'/portrait/(?:small|medium|header)/')
    _VEREIN_ID_RE = re.compile(r'/verein/(\d+)')
    _WETTBEWERB_ID_RE = re.compile(r'/wettbewerb/([A-Za-z0-9]+)(?:$|[/?])')
    _WETTBEWERB_ID_RE_V2 = re.compile(r'/[pw]okal?wettbewerb/([A-Za-z0-9]+)(?:$|[/?])')
    _FOREIGNERS_RE = re.compile(r'(\d+)\s*\((\d+)%\)?')
    _VALUE_RE = re.compile(r'€\s*([\d.,]+)\s*(mi\.|mil\.)')
    _AGE_MIN = 15
    _AGE_MAX = 45
    _BIRTH_PLACE_KEYS = frozenset({'Local de nascimento', 'Place of birth'})

    @classmethod
    def _extract_photo_url(cls, inline: Tag) -> str:
        photo_tag = inline.find('img', class_='bilderrahmen-fixed')
        if not photo_tag or not isinstance(photo_tag, Tag):
            return ''
        src = photo_tag.get('data-src') or photo_tag.get('src', '')
        src_str = str(src)
        if src_str.startswith('data:'):
            return ''
        return cls._PORTRAIT_SIZE_RE.sub('/portrait/big/', src_str)

    @staticmethod
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

    @staticmethod
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

    @classmethod
    def _extract_badge_id(cls, row: Tag) -> str:
        for img in row.find_all('img'):
            if not isinstance(img, Tag):
                continue
            src = str(img.get('src', '') or img.get('data-src', ''))
            m = cls._CLUB_ID_RE.search(src)
            if m:
                return m.group(1)
        return ''

    @staticmethod
    def _extract_country(row: Tag) -> str:
        img = row.find('img', class_='flaggenrahmen')
        return str(img.get('title', '')) if img and isinstance(img, Tag) else ''

    @staticmethod
    def _first_href_match(row: Tag, fragment: str, pattern: re.Pattern[str]) -> str:
        for link in row.find_all('a', href=lambda h: bool(h and fragment in str(h))):
            if not isinstance(link, Tag):
                continue
            m = pattern.search(str(link.get('href', '')))
            if m:
                return m.group(1)
        return ''

    @classmethod
    def _extract_squad_stats(cls, row: Tag) -> tuple[str, str, str, str]:
        cells = [td for td in row.find_all('td', class_='zentriert') if isinstance(td, Tag)]
        integers: list[str] = []
        avg_age = ''
        foreigners_count = ''
        foreigners_pct = ''

        for td in cells:
            text = td.get_text(strip=True)
            if not text:
                continue
            m = cls._FOREIGNERS_RE.search(text)
            if m:
                foreigners_count = m.group(1)
                foreigners_pct = m.group(2)
                continue
            clean = text.replace(',', '.')
            try:
                val = float(clean)
                if ('.' in clean or ',' in text) and cls._AGE_MIN <= val <= cls._AGE_MAX:
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
