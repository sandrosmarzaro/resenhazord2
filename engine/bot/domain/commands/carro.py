"""Random car with FIPE price and Wikipedia/Commons image."""

import random
import re
from typing import ClassVar
from urllib.parse import quote

import httpx
import structlog

from bot.data.car_brands import FIPE_BRANDS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class CarroCommand(Command):
    FIPE_BASE = 'https://parallelum.com.br/fipe/api/v1/carros/marcas'
    WIKI_API = 'https://en.wikipedia.org/w/api.php'
    COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
    WIKI_UA = 'ResenhazordBot/2.0 (https://github.com/smarzaro/resenhazord2; bot@resenhazord.com)'
    FIPE_TIMEOUT = 8.0
    WIKI_TIMEOUT = 8.0
    IMG_TIMEOUT = 12.0
    MAX_YEAR_RETRIES = 3

    SPEC_TOKEN = re.compile(r'^\d+\.\d|^\d+[pP]$|\d+cv$', re.IGNORECASE)
    SPEC_WORD_BASE: ClassVar[set[str]] = {
        'flex',
        'gasolina',
        'diesel',
        'aut.',
        'mec.',
        'cvt',
        'turbo',
    }
    SPEC_WORD_WIKI: ClassVar[set[str]] = {
        'flex',
        'gasolina',
        'diesel',
        'aut',
        'mec',
        'cvt',
        'turbo',
        'sedan',
        'hatch',
        'sw',
        'furgão',
        'furgao',
        'cabine',
        'pickup',
        'dlx',
        'lx',
        'lxl',
        'ex',
        'elx',
        'glx',
        'gls',
        'gli',
        'vip',
        'luxury',
        'elite',
        'premium',
        'limited',
        'sport',
        'comfort',
        'exclusive',
        'country',
        'land',
        'adv',
        'ext',
        'adventure',
    }

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='carro',
            flags=['show', 'dm', 'wiki'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba a foto de um carro aleatório com modelo, ano e preço FIPE.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            brand = random.choice(FIPE_BRANDS)  # noqa: S311
            base = f'{self.FIPE_BASE}/{brand.fipe_code}'

            models_res = await HttpClient.get(f'{base}/modelos', timeout=self.FIPE_TIMEOUT)
            models_data = models_res.json()
            model = random.choice(models_data['modelos'])  # noqa: S311

            years_res = await HttpClient.get(
                f'{base}/modelos/{model["codigo"]}/anos', timeout=self.FIPE_TIMEOUT
            )
            years = years_res.json()

            details = await self._fetch_details(base, model['codigo'], years)
            caption = self._build_caption(brand, model, details)

            base_name = self._base_model_name(model['nome'])
            wiki_name = self._wiki_model_name(model['nome'])
            try:
                thumb = await self._find_image(brand.name, wiki_name, base_name, parsed)
            except (httpx.HTTPError, KeyError, ValueError):
                logger.warning('carro_image_search_failed', brand=brand.name, model=model['nome'])
                thumb = None

            if not thumb:
                return [Reply.to(data).text(caption)]

            buffer = await HttpClient.get_buffer(
                thumb,
                timeout=self.IMG_TIMEOUT,
                headers={'User-Agent': self.WIKI_UA},
            )
            return [Reply.to(data).image_buffer(buffer, caption)]
        except Exception:
            logger.exception('carro_command_error')
            return [Reply.to(data).text('Erro ao buscar carro. Tente novamente mais tarde! 🚗')]

    async def _fetch_details(self, base: str, model_code: int, years: list[dict]) -> dict | None:
        shuffled = years.copy()
        random.shuffle(shuffled)
        for year in shuffled[: self.MAX_YEAR_RETRIES]:
            res = await HttpClient.get(
                f'{base}/modelos/{model_code}/anos/{year["codigo"]}',
                timeout=self.FIPE_TIMEOUT,
            )
            data = res.json()
            if 'error' not in data:
                return data
        return None

    def _build_caption(self, brand, model: dict, details: dict | None) -> str:
        if details:
            return '\n'.join(
                [
                    f'{brand.emoji} *{details["Marca"]} {details["Modelo"]}*',
                    f'📅 {details["AnoModelo"]} | ⛽ {details["Combustivel"]}',
                    f'💰 {details["Valor"]}',
                    brand.origin,
                ]
            )
        return f'{brand.emoji} *{brand.name} {model["nome"]}*\n{brand.origin}'

    async def _find_image(
        self, brand_name: str, wiki_name: str, base_name: str, parsed: ParsedCommand
    ) -> str | None:
        search_term = quote(f'{brand_name} {wiki_name} car')
        wiki_url = (
            f'{self.WIKI_API}?action=query&generator=search'
            f'&gsrsearch={search_term}&gsrlimit=1&prop=pageimages&pithumbsize=640&format=json'
        )
        wiki_res = await HttpClient.get(
            wiki_url,
            timeout=self.WIKI_TIMEOUT,
            headers={'User-Agent': self.WIKI_UA},
        )
        wiki_data = wiki_res.json()
        pages = (wiki_data.get('query') or {}).get('pages') or {}
        first_page = next(iter(pages.values()), {})
        page_title = first_page.get('title', '')
        raw_thumb = (first_page.get('thumbnail') or {}).get('source')

        is_brand_only = self._is_brand_only_page(brand_name, page_title)
        thumb = None if is_brand_only else raw_thumb

        if not thumb and 'wiki' not in parsed.flags:
            thumb = await self._search_commons(brand_name, base_name)

        return thumb

    def _is_brand_only_page(self, brand_name: str, page_title: str) -> bool:
        if not page_title:
            return False
        brand_lower = brand_name.lower()
        title_lower = page_title.lower()
        if title_lower == brand_lower:
            return True
        escaped = re.escape(brand_lower)
        pattern = rf'^{escaped}\s+(?:motors?|automobiles?|automotive|group|corporation)$'
        return bool(re.match(pattern, title_lower))

    async def _search_commons(self, brand_name: str, base_name: str) -> str | None:
        commons_search = quote(f'{brand_name} {base_name}')
        commons_url = (
            f'{self.COMMONS_API}?action=query&generator=search'
            f'&gsrsearch={commons_search}&gsrnamespace=6&gsrlimit=1'
            f'&prop=pageimages&pithumbsize=640&format=json'
        )
        commons_res = await HttpClient.get(
            commons_url,
            timeout=self.WIKI_TIMEOUT,
            headers={'User-Agent': self.WIKI_UA},
        )
        commons_data = commons_res.json()
        commons_pages = (commons_data.get('query') or {}).get('pages') or {}
        first = next(iter(commons_pages.values()), {})
        return (first.get('thumbnail') or {}).get('source')

    @classmethod
    def _base_model_name(cls, nome: str) -> str:
        words = nome.strip().split()
        stop = next(
            (
                i
                for i, w in enumerate(words)
                if cls.SPEC_TOKEN.match(w) or w.lower() in cls.SPEC_WORD_BASE
            ),
            -1,
        )
        return ' '.join(words[:stop] if stop > 0 else words)

    @classmethod
    def _wiki_model_name(cls, nome: str) -> str:
        words = []
        for token in nome.strip().split():
            words.extend(token.split('/'))
        stop = next(
            (
                i
                for i, w in enumerate(words)
                if cls.SPEC_TOKEN.match(w) or w.rstrip('.,').lower() in cls.SPEC_WORD_WIKI
            ),
            -1,
        )
        return ' '.join(words[:stop] if stop > 0 else words)
