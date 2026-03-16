import random

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

TOTAL_AYAHS = 6236


class AlcoraoCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='alcorão', category='aleatórias')

    @property
    def menu_description(self) -> str:
        return 'Receba um versículo aleatório do Alcorão em português.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        ayah_number = random.randint(1, TOTAL_AYAHS)  # noqa: S311
        url = f'https://api.alquran.cloud/v1/ayah/{ayah_number}/pt.elhayek'
        response = await HttpClient.get(url)
        response.raise_for_status()
        ayah = response.json()['data']
        surah = ayah['surah']
        name = surah['englishName']
        ref = f'{surah["number"]}:{ayah["numberInSurah"]}'
        text = f'*{name} {ref}*\n\n> {ayah["text"]}'
        return [Reply.to(data).text(text)]
