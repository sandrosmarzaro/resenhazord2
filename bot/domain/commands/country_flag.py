import random

import structlog

from bot.data.country_flag import DRIVING_SIDE_PT, REGION_MAP, SUBREGION_PT
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.translator import Translator
from bot.infrastructure.restcountries_client import RestCountriesClient

logger = structlog.get_logger()


class CountryFlagCommand(Command):
    MAX_CALLING_CODES = 3

    def __init__(self, api_key: str = '') -> None:
        super().__init__()
        self._catalog = RestCountriesClient(api_key)

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
            countries = await self._catalog.fetch()
            renderable = [country for country in countries if self._has_flag(country)]
            country = random.choice(renderable)
            names = country.get('names', {})
            common_pt = await Translator.to_pt(names.get('common', ''))
            official_pt = await Translator.to_pt(names.get('official', ''))
            country = {**country, 'names': {**names, 'common': common_pt, 'official': official_pt}}
            caption = self._build_caption(country, detail='detail' in parsed.flags)
            flag_png = country.get('flag', {}).get('url_png', '')
            return [Reply.to(data).image(flag_png, caption)]
        except Exception:
            logger.exception('country_flag_fetch_error')
            return [Reply.to(data).text('Erro ao buscar bandeira. Tente novamente mais tarde! 🌍')]

    @staticmethod
    def _has_flag(country: dict) -> bool:
        return bool(country.get('flag', {}).get('url_png'))

    @staticmethod
    def _build_caption(country: dict, *, detail: bool = False) -> str:
        region = country.get('region', '')
        region_info = REGION_MAP.get(region, {'emoji': '🌐', 'label': region})
        subregion = country.get('subregion')
        if subregion:
            subregion_pt = SUBREGION_PT.get(subregion, subregion)
            location_line = f'{region_info["emoji"]} {region_info["label"]} · {subregion_pt}'
        else:
            location_line = f'{region_info["emoji"]} {region_info["label"]}'

        capitals = country.get('capitals', [])
        capital = capitals[0]['name'] if capitals else 'N/A'
        population = f'{country.get("population", 0):,}'.replace(',', '.')
        area_km = country.get('area', {}).get('kilometers', 0)
        area = f'{round(area_km):,}'.replace(',', '.')
        languages = (
            ', '.join(language['name'] for language in country.get('languages', [])) or 'N/A'
        )
        currencies = (
            ' / '.join(
                f'{currency["name"]} ({currency["code"]})'
                for currency in country.get('currencies', [])
            )
            or 'N/A'
        )

        names = country.get('names', {})
        flag_emoji = country.get('flag', {}).get('emoji', '')
        lines = [f'*{names.get("common", "")}* {flag_emoji}']
        if names.get('official') != names.get('common'):
            lines.append(f'_{names.get("official", "")}_')
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

        coordinates = country.get('coordinates', {})
        latitude = coordinates.get('lat')
        longitude = coordinates.get('lng')
        if latitude is not None and longitude is not None:
            lines.append(f'📍 {latitude:.2f}, {longitude:.2f}')

        calling_codes = country.get('calling_codes', [])
        if calling_codes:
            codes = ', '.join(
                f'+{code}' for code in calling_codes[: CountryFlagCommand.MAX_CALLING_CODES]
            )
            lines.append(f'📞 {codes}')

        borders = country.get('borders', [])
        if borders:
            lines.append(f'🗺️ {", ".join(borders)}')

        driving_side = country.get('cars', {}).get('driving_side', '')
        if driving_side:
            lines.append(f'🚗 {DRIVING_SIDE_PT.get(driving_side, driving_side)}')

        return lines
