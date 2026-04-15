"""Competition info parsing for live matches."""

from bs4 import Tag

from bot.data.nationality_flags import nationality_flag
from bot.data.transfermarkt_country_codes import (
    COMPETITION_CODE_OVERRIDES,
    COUNTRY_CODE_TO_FLAG,
)
from bot.domain.services.transfermarkt.match_row_parser import CompetitionContext
from bot.domain.services.transfermarkt.parse_helpers import ParseHelpers


class CompetitionParser(ParseHelpers):
    @classmethod
    def extract_competition_info(
        cls, header: Tag, *, flag_search_in: Tag
    ) -> tuple[str, str, str, str] | None:
        comp_link = header.find('a')
        comp_name = ''
        comp_href = ''
        if comp_link and isinstance(comp_link, Tag):
            comp_name = comp_link.get_text(strip=True)
            comp_href = str(comp_link.get('href', ''))

        comp_code = ''
        if comp_href:
            m = cls._WETTBEWERB_ID_RE.search(comp_href)
            if not m:
                m = cls._WETTBEWERB_ID_RE_V2.search(comp_href)
            if m:
                comp_code = m.group(1)

        country = ''
        flag_img = flag_search_in.find('img', class_='wettbewerblogo')
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
    def find_livescore_table_for_kategorie(cls, kategorie: Tag) -> Tag | None:
        for sibling in kategorie.find_next_siblings():
            if not isinstance(sibling, Tag):
                continue
            classes = sibling.get('class') or []
            if sibling.name == 'table' and 'livescore' in classes:
                return sibling
            if sibling.name == 'div' and 'kategorie' in classes:
                break
        return None

    @classmethod
    def build_competition_context(
        cls, header: Tag, *, flag_search_in: Tag
    ) -> CompetitionContext | None:
        comp_info = cls.extract_competition_info(header, flag_search_in=flag_search_in)
        if not comp_info:
            return None
        return CompetitionContext(*comp_info)
