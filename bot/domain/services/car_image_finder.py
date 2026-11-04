from typing import ClassVar

import httpx
import structlog

from bot.domain.services.car_model_name import CarModelName
from bot.infrastructure.wikimedia_client import WikimediaClient

logger = structlog.get_logger()


class CarImageFinder:
    _LOOKUP_ERRORS: ClassVar[tuple[type[Exception], ...]] = (httpx.HTTPError, KeyError, ValueError)

    @classmethod
    async def find(cls, brand_name: str, model_name: str, *, wiki_only: bool) -> str | None:
        try:
            thumb = await cls._find_model_image(brand_name, model_name, wiki_only=wiki_only)
        except cls._LOOKUP_ERRORS:
            logger.warning(
                'upstream_failed', upstream='wikipedia', brand=brand_name, model=model_name
            )
            thumb = None
        if thumb:
            return thumb
        try:
            return await cls._find_brand_logo(brand_name)
        except cls._LOOKUP_ERRORS:
            return None

    @classmethod
    async def _find_model_image(
        cls, brand_name: str, model_name: str, *, wiki_only: bool
    ) -> str | None:
        wiki_name = CarModelName.wiki(model_name)
        page = await WikimediaClient.search_wikipedia(f'{brand_name} {wiki_name} car')
        if page.thumbnail and not CarModelName.is_brand_only_page(page.title):
            return page.thumbnail
        if wiki_only:
            return None
        base_name = CarModelName.base(model_name)
        commons = await WikimediaClient.search_commons_files(f'{brand_name} {base_name}')
        return commons.thumbnail

    @classmethod
    async def _find_brand_logo(cls, brand_name: str) -> str | None:
        page = await WikimediaClient.search_wikipedia(f'{brand_name} automobile manufacturer')
        return page.thumbnail
