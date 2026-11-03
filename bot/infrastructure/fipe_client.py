from http import HTTPStatus
from typing import Any

import httpx

from bot.infrastructure.http_client import HttpClient


class FipeClient:
    BASE_URL = 'https://parallelum.com.br/fipe/api/v1/carros/marcas'
    TIMEOUT = 8.0

    @classmethod
    async def models(cls, brand_code: str) -> list[dict[str, Any]]:
        response = await cls._get(f'{brand_code}/modelos')
        response.raise_for_status()
        return response.json()['modelos']

    @classmethod
    async def years(cls, brand_code: str, model_code: int) -> list[dict[str, Any]]:
        response = await cls._get(f'{brand_code}/modelos/{model_code}/anos')
        response.raise_for_status()
        return response.json()

    @classmethod
    async def details(cls, brand_code: str, model_code: int, year_code: str) -> dict[str, Any]:
        # A year FIPE has no price for answers 404 with an {"error": ...} body, which the
        # caller reads as "try the next year".
        response = await cls._get(f'{brand_code}/modelos/{model_code}/anos/{year_code}')
        if response.status_code != HTTPStatus.NOT_FOUND:
            response.raise_for_status()
        return response.json()

    @classmethod
    async def _get(cls, path: str) -> httpx.Response:
        return await HttpClient.get(f'{cls.BASE_URL}/{path}', timeout=cls.TIMEOUT)
