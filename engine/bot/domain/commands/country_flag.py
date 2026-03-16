import random

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()

REGION_MAP = {
    'Africa': {'emoji': '🌍', 'label': 'África'},
    'Americas': {'emoji': '🌎', 'label': 'Américas'},
    'Antarctic': {'emoji': '🌐', 'label': 'Antártida'},
    'Asia': {'emoji': '🌏', 'label': 'Ásia'},
    'Europe': {'emoji': '🌍', 'label': 'Europa'},
    'Oceania': {'emoji': '🌏', 'label': 'Oceania'},
}

SUBREGION_PT = {
    'South America': 'América do Sul',
    'North America': 'América do Norte',
    'Central America': 'América Central',
    'Caribbean': 'Caribe',
    'Northern Africa': 'África do Norte',
    'Western Africa': 'África Ocidental',
    'Eastern Africa': 'África Oriental',
    'Middle Africa': 'África Central',
    'Southern Africa': 'África Austral',
    'Western Europe': 'Europa Ocidental',
    'Northern Europe': 'Europa do Norte',
    'Eastern Europe': 'Europa do Leste',
    'Southern Europe': 'Europa do Sul',
    'Central Asia': 'Ásia Central',
    'Western Asia': 'Ásia Ocidental',
    'Eastern Asia': 'Ásia Oriental',
    'South Asia': 'Sul da Ásia',
    'Southeast Asia': 'Sudeste Asiático',
    'Melanesia': 'Melanésia',
    'Micronesia': 'Micronésia',
    'Polynesia': 'Polinésia',
    'Australia and New Zealand': 'Austrália e Nova Zelândia',
}

API_URL = (
    'https://restcountries.com/v3.1/all'
    '?fields=name,flags,flag,capital,region,subregion,population,area,languages,currencies'
)


class CountryFlagCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='bandeira', flags=['show', 'dm'], category='aleatórias')

    @property
    def menu_description(self) -> str:
        return 'Envia a bandeira de um país aleatório com informações.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            response = await HttpClient.get(API_URL)
            response.raise_for_status()
            countries = response.json()
            country = random.choice(countries)  # noqa: S311
            caption = self._build_caption(country)
            return [Reply.to(data).image(country['flags']['png'], caption)]
        except Exception:
            logger.exception('country_flag_fetch_error')
            return [Reply.to(data).text('Erro ao buscar bandeira. Tente novamente mais tarde! 🌍')]

    @staticmethod
    def _build_caption(country: dict) -> str:
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
        lines.append(f'🏙️ Capital: {capital}')
        lines.append(f'👥 {population} habitantes')
        lines.append(f'📐 {area} km²')
        lines.append(f'🗣️ {languages}')
        lines.append(f'💰 {currencies}')

        return '\n'.join(lines)
