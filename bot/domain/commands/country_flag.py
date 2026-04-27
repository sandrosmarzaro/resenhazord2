import random

import structlog

from bot.data.country_flag import DRIVING_SIDE_PT, REGION_MAP, SUBREGION_PT
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.translator import Translator
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class CountryFlagCommand(Command):
    BASE_FIELDS = 'name,flags,cca3,capital,region,subregion,population,area,languages,currencies'
    API_URL = f'https://restcountries.com/v3.1/all?fields={BASE_FIELDS}'
    DETAIL_FIELDS = 'timezones,borders,idd,latlng,car'
    DETAIL_URL = 'https://restcountries.com/v3.1/alpha/{code}?fields={fields}'
    LATLNG_PAIR_LEN = 2
    MAX_IDD_SUFFIXES = 3

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='bandeira',
            aliases=['flag'],
            flags=[Flag.SHOW, Flag.DM, 'detail'],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Envia a bandeira de um país aleatório com informações.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            response = await HttpClient.get(self.API_URL)
            response.raise_for_status()
            countries = response.json()
            country = random.choice(countries)  # noqa: S311
            detail = 'detail' in parsed.flags
            if detail:
                country = await self._fetch_detail(country)
            name = country.get('name', {})
            common_pt = await Translator.to_pt(name.get('common', ''))
            official_pt = await Translator.to_pt(name.get('official', ''))
            country = {**country, 'name': {**name, 'common': common_pt, 'official': official_pt}}
            caption = self._build_caption(country, detail=detail)
            return [Reply.to(data).image(country['flags']['png'], caption)]
        except Exception:
            logger.exception('country_flag_fetch_error')
            return [Reply.to(data).text('Erro ao buscar bandeira. Tente novamente mais tarde! 🌍')]

    async def _fetch_detail(self, country: dict) -> dict:
        url = self.DETAIL_URL.format(code=country['cca3'], fields=self.DETAIL_FIELDS)
        response = await HttpClient.get(url)
        response.raise_for_status()
        return {**country, **response.json()}

    @staticmethod
    def _build_caption(country: dict, *, detail: bool = False) -> str:
        region_info = REGION_MAP.get(
            country.get('region', ''), {'emoji': '🌐', 'label': country.get('region', '')}
        )
        subregion = country.get('subregion')
        if subregion:
            subregion_pt = SUBREGION_PT.get(subregion, subregion)
            location_line = f'{region_info["emoji"]} {region_info["label"]} · {subregion_pt}'
        else:
            location_line = f'{region_info["emoji"]} {region_info["label"]}'

        capitals = country.get('capital', [])
        capital = capitals[0] if capitals else 'N/A'
        population = f'{country.get("population", 0):,}'.replace(',', '.')
        area = f'{round(country.get("area", 0)):,}'.replace(',', '.')
        languages = ', '.join(country.get('languages', {}).values()) or 'N/A'

        currencies_data = country.get('currencies', {})
        currencies = (
            ' / '.join(f'{c["name"]} ({code})' for code, c in currencies_data.items()) or 'N/A'
        )

        name = country.get('name', {})
        lines = [f'*{name.get("common", "")}* {country.get("flag", "")}']
        if name.get('official') != name.get('common'):
            lines.append(f'_{name.get("official", "")}_')
        lines.append('')
        lines.append(location_line)
        lines.append(f'🏙️ {capital}')
        lines.append(f'👥 {population} habitantes')
        lines.append(f'📐 {area} km²')
        lines.append(f'🗣️ {languages}')
        lines.append(f'💰 {currencies}')

        if detail:
            lines.extend(CountryFlagCommand._build_detail_lines(country))

        return '\n'.join(lines)

    @staticmethod
    def _build_detail_lines(country: dict) -> list[str]:
        lines = ['']
        timezones = country.get('timezones', [])
        if timezones:
            lines.append(f'🕐 {", ".join(timezones)}')

        latlng = country.get('latlng', [])
        if len(latlng) == CountryFlagCommand.LATLNG_PAIR_LEN:
            lines.append(f'📍 {latlng[0]:.2f}, {latlng[1]:.2f}')

        idd = country.get('idd', {})
        root = idd.get('root', '')
        suffixes = idd.get('suffixes', [])
        if root and suffixes:
            codes = ', '.join(f'{root}{s}' for s in suffixes[: CountryFlagCommand.MAX_IDD_SUFFIXES])
            lines.append(f'📞 {codes}')

        borders = country.get('borders', [])
        if borders:
            lines.append(f'🗺️ {", ".join(borders)}')

        car = country.get('car', {})
        side = car.get('side', '')
        if side:
            lines.append(f'🚗 {DRIVING_SIDE_PT.get(side, side)}')

        return lines
