import random
import re
from http import HTTPStatus
from re import Pattern
from typing import ClassVar

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from bot.data.browser_headers import BROWSER_HEADERS
from bot.data.nsfw_tags import MINOR_TAG_TERMS
from bot.domain.exceptions import ExternalServiceError
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class Rule34Images:
    """Finds one image: on rule34.xxx, which answers a CAPTCHA now and then, or on paheal.

    Both are filtered by tags people write, which reduces the risk of a post depicting
    minors and can't rule it out, so a barely tagged post isn't sent at all."""

    RANDOM_PAGE_URL = 'https://rule34.xxx/index.php?page=post&s=random'
    POSTS_URL = 'https://rule34.paheal.net/api/danbooru/find_posts'
    REQUEST_TIMEOUT_SECONDS = 30.0
    PAGE_SIZE = 25
    # Inside the 260k pages of 2026, and the archive only grows.
    MAX_PAGE = 200_000
    IMAGE_EXTENSIONS: ClassVar[tuple[str, ...]] = ('.png', '.jpg', '.jpeg')
    # The gateway hands these URLs to Baileys, which would also read a local path.
    RULE34_CDN_URL: ClassVar[Pattern[str]] = re.compile(
        r'https://[a-z0-9-]+\.rule34\.xxx/[\w/.?=&-]+'
    )
    PAHEAL_CDN_URL: ClassVar[Pattern[str]] = re.compile(
        r'https://[a-z0-9-]+\.paheal-cdn\.net/[\w/.-]+'
    )
    # What uploaders leave on a post nobody has tagged yet.
    PLACEHOLDER_TAG = 'tagme'
    MIN_TAGS = 3

    @classmethod
    async def fetch(cls) -> str:
        return await cls._from_rule34() or await cls._from_paheal()

    @classmethod
    async def _from_rule34(cls) -> str | None:
        try:
            response = await HttpClient.get(
                cls.RANDOM_PAGE_URL,
                timeout=cls.REQUEST_TIMEOUT_SECONDS,
                headers=BROWSER_HEADERS,
            )
            if response.status_code == HTTPStatus.FORBIDDEN:
                logger.info('rule34_fallback', reason='captcha')
                return None
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning('upstream_failed', upstream='rule34', error=str(error))
            return None
        return cls._image_of(BeautifulSoup(response.text, 'html.parser'))

    @classmethod
    def _image_of(cls, page: BeautifulSoup) -> str | None:
        # Skips the banner that shares the box, and a video post has no image at all.
        images = [
            image
            for image in page.select('div.flexi img')
            if cls.RULE34_CDN_URL.fullmatch(str(image.get('src')))
        ]
        if not images:
            logger.info('rule34_fallback', reason='no_image')
            return None
        sidebar = [link.text for link in page.select('#tag-sidebar li a[href*="tags="]')]
        tags = [*str(images[0].get('alt', '')).split(), *sidebar]
        if not cls._can_vouch_for(tags):
            logger.info('rule34_fallback', reason='unverified')
            return None
        return str(images[0]['src'])

    @classmethod
    async def _from_paheal(cls) -> str:
        response = await HttpClient.get(
            cls.POSTS_URL,
            params={'limit': cls.PAGE_SIZE, 'page': random.randint(1, cls.MAX_PAGE)},
            timeout=cls.REQUEST_TIMEOUT_SECONDS,
            headers=BROWSER_HEADERS,
        )
        response.raise_for_status()

        posts = BeautifulSoup(response.text, 'html.parser').select('post')
        images = [str(post['file_url']) for post in posts if cls._is_sendable(post)]
        if not images:
            msg = 'Nenhuma imagem encontrada'
            raise ExternalServiceError(msg)
        return random.choice(images)

    @classmethod
    def _is_sendable(cls, post: Tag) -> bool:
        # Filtered here and not in the search: the API refuses a longer negative query,
        # and a shorter one takes seconds on deep pages.
        file_name = str(post['file_name']).lower()
        return (
            cls._can_vouch_for([*str(post['tags']).split(), file_name])
            and file_name.endswith(cls.IMAGE_EXTENSIONS)
            and cls.PAHEAL_CDN_URL.fullmatch(str(post['file_url'])) is not None
        )

    @classmethod
    def _can_vouch_for(cls, tags: list[str]) -> bool:
        lowered = [tag.lower() for tag in tags]
        return (
            len(lowered) >= cls.MIN_TAGS
            and cls.PLACEHOLDER_TAG not in lowered
            and not any(term in tag for tag in lowered for term in MINOR_TAG_TERMS)
        )
