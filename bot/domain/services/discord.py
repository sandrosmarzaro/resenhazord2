"""Discord REST API client for channel management and media upload."""

import re
import unicodedata

import structlog

from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class DiscordService:
    CATEGORY_TYPE = 4
    TEXT_CHANNEL_TYPE = 0
    BASE_URL = 'https://discord.com/api/v10'

    def __init__(self, token: str, guild_id: str) -> None:
        self._headers = {'Authorization': f'Bot {token}'}
        self._guild_id = guild_id

    @staticmethod
    def _normalize(name: str) -> str:
        normalized = unicodedata.normalize('NFD', name.lower())
        stripped = ''.join(c for c in normalized if not unicodedata.combining(c))
        return re.sub(r'\s+', '-', stripped)

    @staticmethod
    def _name_matches(channel_name: str, search_name: str) -> bool:
        a, b = channel_name.lower(), search_name.lower()
        return a == b or DiscordService._normalize(a) == DiscordService._normalize(b)

    async def get_channels(self) -> list[dict]:
        url = f'{self.BASE_URL}/guilds/{self._guild_id}/channels'
        response = await HttpClient.get(url, headers=self._headers)
        response.raise_for_status()
        return response.json()

    def find_category(self, channels: list[dict], name: str) -> dict | None:
        return next(
            (
                c
                for c in channels
                if c['type'] == self.CATEGORY_TYPE and self._name_matches(c['name'], name)
            ),
            None,
        )

    def find_channel(self, channels: list[dict], name: str, parent_id: str) -> dict | None:
        return next(
            (
                c
                for c in channels
                if c['type'] == self.TEXT_CHANNEL_TYPE
                and self._name_matches(c['name'], name)
                and c.get('parent_id') == parent_id
            ),
            None,
        )

    async def create_category(self, name: str) -> dict:
        url = f'{self.BASE_URL}/guilds/{self._guild_id}/channels'
        response = await HttpClient.post(
            url,
            json={'name': self._normalize(name), 'type': self.CATEGORY_TYPE},
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()

    async def create_channel(self, name: str, parent_id: str) -> dict:
        url = f'{self.BASE_URL}/guilds/{self._guild_id}/channels'
        response = await HttpClient.post(
            url,
            json={
                'name': self._normalize(name),
                'type': self.TEXT_CHANNEL_TYPE,
                'parent_id': parent_id,
            },
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()

    async def upload_media(self, channel_id: str, buffer: bytes, filename: str) -> None:
        url = f'{self.BASE_URL}/channels/{channel_id}/messages'
        response = await HttpClient.post(
            url,
            files={'files[0]': (filename, buffer)},
            headers=self._headers,
        )
        response.raise_for_status()
