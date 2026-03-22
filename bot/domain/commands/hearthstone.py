import random
import re

import anyio
import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import CommandConfig, ParsedCommand
from bot.domain.commands.card_booster import CardBoosterCommand, CardItem
from bot.domain.exceptions import ExternalServiceError
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

    def __init__(self, *, bnet_id: str = '', bnet_secret: str = '') -> None:
        super().__init__()
        self._bnet_id = bnet_id
        self._bnet_secret = bnet_secret

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='hs',
            aliases=['hearthstone'],
            flags=['booster', 'show', 'dm'],
            category='random',
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

        caption = self._build_caption(card)

        image_url = self._safe_text(card.get('image', ''))
        if not image_url:
            return [Reply.to(data).text('Essa carta não tem imagem. Tente novamente.')]

        return [Reply.to(data).image(image_url, caption)]

    async def _fetch_booster_items(self) -> list[CardItem]:
        token = await self._get_access_token()
        if not token:
            msg = 'Hearthstone: OAuth token unavailable'
            raise ExternalServiceError(msg)

        headers = {'Authorization': f'Bearer {token}'}
        first = await HttpClient.get(self.API_URL, headers=headers, params={'pageSize': 1})
        first.raise_for_status()
        page_count = first.json()['pageCount']

        pages = [random.randint(1, page_count) for _ in range(self.BOOSTER_CONFIG.count)]  # noqa: S311
        results: list[CardItem | None] = [None] * len(pages)

        async def _fetch(index: int, page: int) -> None:
            response = await HttpClient.get(
                self.API_URL, headers=headers, params={'page': page, 'pageSize': 1}
            )
            response.raise_for_status()
            card = response.json()['cards'][0]
            image_url = self._safe_text(card.get('image', ''))
            label = self._safe_text(card.get('name', ''))
            results[index] = CardItem(image_url=image_url, label=label)

        async with anyio.create_task_group() as tg:
            for i, page in enumerate(pages):
                tg.start_soon(_fetch, i, page)

        items: list[CardItem] = [r for r in results if r is not None]

        return items

    @staticmethod
    def _safe_text(value: object) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return str(value.get('pt_BR', value.get('en_US', next(iter(value.values()), ''))))
        return ''

    def _build_caption(self, card: dict) -> str:
        name = self._safe_text(card.get('name', ''))
        lines: list[str] = [f'*{name}*']

        stats: list[str] = []
        if card.get('manaCost') is not None:
            stats.append(f'💎 {card["manaCost"]}')
        if card.get('attack') is not None:
            stats.append(f'⚔️ {card["attack"]}')
        if card.get('health') is not None:
            stats.append(f'❤️ {card["health"]}')
        if stats:
            lines.append('   '.join(stats))

        raw_text = self._safe_text(card.get('text', ''))
        description = self.BOLD_RE.sub('*', raw_text)
        description = self.ITALIC_RE.sub('_', description)
        if description:
            lines.append(f'\n> {description}')

        flavor = self._safe_text(card.get('flavorText', ''))
        if flavor:
            lines.append(f'\n_{flavor}_')

        return '\n'.join(lines)

    async def _get_access_token(self) -> str | None:
        if HearthstoneCommand._cached_token:
            return HearthstoneCommand._cached_token

        if not self._bnet_id or not self._bnet_secret:
            return None

        try:
            response = await HttpClient.post(
                self.TOKEN_URL,
                data='grant_type=client_credentials',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=(self._bnet_id, self._bnet_secret),
            )
            response.raise_for_status()
            HearthstoneCommand._cached_token = response.json()['access_token']
        except Exception:
            logger.exception('hearthstone_oauth_failed')
            return None
        else:
            return HearthstoneCommand._cached_token
