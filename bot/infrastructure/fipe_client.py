from typing import Any

from bot.infrastructure.http_client import HttpClient


class FipeClient:
    BASE_URL = 'https://parallelum.com.br/fipe/api/v1/carros/marcas'
    TIMEOUT = 8.0

    @classmethod
    async def models(cls, brand_code: str) -> list[dict[str, Any]]:
        data = await cls._get(f'{brand_code}/modelos')
        return data['modelos']

    @classmethod
    async def years(cls, brand_code: str, model_code: int) -> list[dict[str, Any]]:
        return await cls._get(f'{brand_code}/modelos/{model_code}/anos')

    @classmethod
    async def details(cls, brand_code: str, model_code: int, year_code: str) -> dict[str, Any]:
        return await cls._get(f'{brand_code}/modelos/{model_code}/anos/{year_code}')

    @classmethod
    async def _get(cls, path: str) -> Any:
        response = await HttpClient.get(f'{cls.BASE_URL}/{path}', timeout=cls.TIMEOUT)
        return response.json()
