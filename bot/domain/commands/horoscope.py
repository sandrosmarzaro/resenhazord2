from bot.data.horoscope import SIGN_LIST_TEXT, SIGN_LOOKUP, SIGN_NAMES, SIGNS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import (
    ArgType,
    Command,
    CommandConfig,
    OptionDef,
    ParsedCommand,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
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
            options=[OptionDef(name='signo', values=SIGN_NAMES)],
            flags=['dm', 'show'],
            category='random',
        )

    @property
    def menu_description(self) -> str:
        return 'Horóscopo diário para o seu signo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        sign_input = parsed.options.get('signo')
        if not sign_input:
            return [Reply.to(data).text(f'Uso: ,horóscopo <signo>\n\n{SIGN_LIST_TEXT}')]

        api_name = SIGN_LOOKUP[sign_input]
        sign = SIGNS[api_name]

        response = await HttpClient.get(self.API_URL, params={'sign': api_name})
        response.raise_for_status()
        horoscope = response.json()['data']['horoscope']

        header = f'{sign.emoji} *{sign.pt_name}* ({sign.dates})'
        return [Reply.to(data).text(f'{header}\n\n> {horoscope}')]
