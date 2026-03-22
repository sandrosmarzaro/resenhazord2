import unicodedata

import httpx
import structlog

from bot.data.horoscope import SIGN_LIST_TEXT, SIGN_LOOKUP, SIGNS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class HoroscopeCommand(Command):
    API_URL = 'https://freehoroscopeapi.com/api/v1/get-horoscope/daily'
    TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='horóscopo',
            aliases=['horoscope'],
            args=ArgType.OPTIONAL,
            args_label='signo',
            flags=['dm', 'show'],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Horóscopo diário para o seu signo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        sign_input = parsed.rest.strip().lower() if parsed.rest else ''
        if not sign_input:
            return [Reply.to(data).text(f'Uso: ,horóscopo <signo>\n\n{SIGN_LIST_TEXT}')]

        normalized = self._strip_accents(sign_input)
        api_name = SIGN_LOOKUP.get(sign_input) or SIGN_LOOKUP.get(normalized)
        if not api_name:
            return [Reply.to(data).text(f'Signo inválido! 🤔\n\n{SIGN_LIST_TEXT}')]
        sign = SIGNS[api_name]

        response = await HttpClient.get(self.API_URL, params={'sign': api_name})
        response.raise_for_status()
        horoscope = response.json()['data']['horoscope']

        horoscope_pt = await self._translate_to_pt(horoscope)

        header = f'{sign.emoji} *{sign.pt_name}* ({sign.dates})'
        return [Reply.to(data).text(f'{header}\n\n{horoscope_pt}')]

    async def _translate_to_pt(self, text: str) -> str:
        try:
            params = {
                'client': 'gtx',
                'sl': 'en',
                'tl': 'pt',
                'dt': 't',
                'q': text,
            }
            response = await HttpClient.get(self.TRANSLATE_URL, params=params)
            response.raise_for_status()
            segments = response.json()[0]
            return ''.join(seg[0] for seg in segments if seg[0])
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            logger.warning('horoscope_translate_failed')
            return text

    @staticmethod
    def _strip_accents(text: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn'
        )
