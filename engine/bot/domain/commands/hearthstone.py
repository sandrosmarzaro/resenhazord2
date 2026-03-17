import os
import random
import re

import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandConfig, ParsedCommand
from bot.domain.commands.card_booster import CardBoosterCommand, CardItem
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class HearthstoneCommand(CardBoosterCommand):
    API_URL = 'https://us.api.blizzard.com/hearthstone/cards?locale=pt_BR'
    TOKEN_URL = 'https://oauth.battle.net/token'  # noqa: S105
    BOLD_RE = re.compile(r'</?b>')
    ITALIC_RE = re.compile(r'</?i>')

    _cached_token: str | None = None

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='hs',
            flags=['booster', 'show', 'dm'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba uma carta aleatória de Hearthstone.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        if 'booster' in parsed.flags:
            return await self._run_booster(data, parsed)

        token = await self._get_access_token()
        if not token:
            return [
                Reply.to(data).text(
                    'Não consegui entrar na Battle.net, manda a Blizzard tomar no cu! 🤷‍♂️'
                )
            ]

        headers = {'Authorization': f'Bearer {token}'}

        first = await HttpClient.get(self.API_URL, headers=headers, params={'pageSize': 1})
        first.raise_for_status()
        page_count = first.json()['pageCount']

        page = random.randint(1, page_count)  # noqa: S311
        response = await HttpClient.get(
            self.API_URL, headers=headers, params={'page': page, 'pageSize': 1}
        )
        response.raise_for_status()
        card = response.json()['cards'][0]

        description = self.BOLD_RE.sub('*', card['text'])
        description = self.ITALIC_RE.sub('_', description)
        caption = f'*{card["name"]}*\n\n> "{card["flavorText"]}"\n\n{description}'

        return [Reply.to(data).image(card['image'], caption)]

    async def _fetch_booster_items(self) -> list[CardItem]:
        token = await self._get_access_token()
        if not token:
            msg = 'Hearthstone: OAuth token unavailable'
            raise ValueError(msg)

        headers = {'Authorization': f'Bearer {token}'}
        first = await HttpClient.get(self.API_URL, headers=headers, params={'pageSize': 1})
        first.raise_for_status()
        page_count = first.json()['pageCount']

        items: list[CardItem] = []
        for _ in range(self.BOOSTER_CONFIG.count):
            page = random.randint(1, page_count)  # noqa: S311
            response = await HttpClient.get(
                self.API_URL, headers=headers, params={'page': page, 'pageSize': 1}
            )
            response.raise_for_status()
            card = response.json()['cards'][0]
            items.append(CardItem(image_url=card['image'], label=card['name']))

        return items

    async def _get_access_token(self) -> str | None:
        if HearthstoneCommand._cached_token:
            return HearthstoneCommand._cached_token

        bnet_id = os.environ.get('BNET_ID', '')
        bnet_secret = os.environ.get('BNET_SECRET', '')
        if not bnet_id or not bnet_secret:
            return None

        try:
            response = await HttpClient.post(
                self.TOKEN_URL,
                data='grant_type=client_credentials',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=(bnet_id, bnet_secret),
            )
            response.raise_for_status()
            HearthstoneCommand._cached_token = response.json()['access_token']
        except Exception:
            logger.exception('hearthstone_oauth_failed')
            return None
        else:
            return HearthstoneCommand._cached_token
