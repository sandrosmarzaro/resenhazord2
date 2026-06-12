import time
from typing import ClassVar

from bot.infrastructure.http_client import HttpClient


class RestCountriesClient:
    BASE_URL = 'https://api.restcountries.com/countries/v5'
    RESPONSE_FIELDS = (
        'names,flag,codes,capitals,region,subregion,population,area,'
        'languages,currencies,timezones,coordinates,calling_codes,borders,cars'
    )
    PAGE_SIZE = 100
    CACHE_TTL_SECONDS = 86400

    _cache: ClassVar[list[dict] | None] = None
    _cache_expiry: ClassVar[float] = 0.0

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def fetch(self) -> list[dict]:
        now = time.monotonic()
        if RestCountriesClient._cache is not None and now < RestCountriesClient._cache_expiry:
            return RestCountriesClient._cache
        countries = await self._fetch_all()
        RestCountriesClient._cache = countries
        RestCountriesClient._cache_expiry = now + self.CACHE_TTL_SECONDS
        return countries

    @classmethod
    def reset_cache(cls) -> None:
        cls._cache = None
        cls._cache_expiry = 0.0

    async def _fetch_all(self) -> list[dict]:
        countries: list[dict] = []
        offset = 0
        while True:
            page = await self._fetch_page(offset)
            countries.extend(page)
            if len(page) < self.PAGE_SIZE:
                return countries
            offset += self.PAGE_SIZE

    async def _fetch_page(self, offset: int) -> list[dict]:
        url = (
            f'{self.BASE_URL}?response_fields={self.RESPONSE_FIELDS}'
            f'&limit={self.PAGE_SIZE}&offset={offset}'
        )
        headers = {'Authorization': f'Bearer {self._api_key}'}
        response = await HttpClient.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['data']['objects']
