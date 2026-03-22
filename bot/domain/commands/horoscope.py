import unicodedata

from bot.data.horoscope import SIGN_LIST_TEXT, SIGN_LOOKUP, SIGNS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.translator import Translator
from bot.infrastructure.http_client import HttpClient


class HoroscopeCommand(Command):
    API_URL = 'https://freehoroscopeapi.com/api/v1/get-horoscope/daily'

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

        horoscope_pt = await Translator.to_pt(horoscope)

        header = f'{sign.emoji} *{sign.pt_name}* ({sign.dates})'
        return [Reply.to(data).text(f'{header}\n\n{horoscope_pt}')]

    @staticmethod
    def _strip_accents(text: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn'
        )
