import random
import re
from re import Pattern
from typing import ClassVar

import structlog
from bs4 import BeautifulSoup, Tag

from bot.data.browser_headers import BROWSER_HEADERS
from bot.data.nsfw_tags import MINOR_TAG_TERMS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    Category,
    Command,
    CommandConfig,
    CommandScope,
    Flag,
    ParsedCommand,
    Platform,
)
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class Rule34Command(Command):
    # rule34.xxx answers a CAPTCHA now, and its API needs an account it won't register
    # from Brazil. Paheal needs no key.
    POSTS_URL = 'https://rule34.paheal.net/api/danbooru/find_posts'
    PAGE_SIZE = 25
    # Inside the 260k pages of 2026, and the archive only grows.
    MAX_PAGE = 200_000
    IMAGE_EXTENSIONS: ClassVar[tuple[str, ...]] = ('.png', '.jpg', '.jpeg')
    # The gateway hands this URL to Baileys, which would also read a local path.
    CDN_URL: ClassVar[Pattern[str]] = re.compile(r'https://[a-z0-9-]+\.paheal-cdn\.net/[\w/.-]+')
    # What uploaders leave on a post nobody has tagged yet.
    PLACEHOLDER_TAG = 'tagme'
    MIN_TAGS = 3

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='rule 34',
            aliases=['rule34', 'rule_34', 'r34'],
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            scope=CommandScope.NSFW,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Recebe uma imagem aleatória da Rule 34 (18+).'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        response = await HttpClient.get(
            self.POSTS_URL,
            params={'limit': self.PAGE_SIZE, 'page': random.randint(1, self.MAX_PAGE)},
            timeout=30.0,
            headers=BROWSER_HEADERS,
        )
        response.raise_for_status()

        posts = BeautifulSoup(response.text, 'html.parser').select('post')
        images = [str(post['file_url']) for post in posts if self._is_sendable(post)]
        if not images:
            msg = 'Nenhuma imagem encontrada'
            raise ExternalServiceError(msg)

        return [Reply.to(data).image(random.choice(images), 'Aqui está a imagem que você pediu 🤗')]

    @classmethod
    def _is_sendable(cls, post: Tag) -> bool:
        # Filtered here and not in the search: the API refuses a longer negative query,
        # and a shorter one takes seconds on deep pages. A denylist over tags people write
        # reduces the risk and can't rule it out, so a barely tagged post isn't sent at all.
        tags = str(post['tags']).lower().split()
        file_name = str(post['file_name']).lower()
        texts = [*tags, file_name]
        return (
            len(tags) >= cls.MIN_TAGS
            and cls.PLACEHOLDER_TAG not in tags
            and file_name.endswith(cls.IMAGE_EXTENSIONS)
            and not any(term in text for text in texts for term in MINOR_TAG_TERMS)
            and cls.CDN_URL.fullmatch(str(post['file_url'])) is not None
        )
