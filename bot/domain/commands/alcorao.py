import random

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, OptionDef, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class AlcoraoCommand(Command):
    TOTAL_AYAHS = 6236

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='alcorão',
            options=[OptionDef(name='lang', values=['ar', 'pt'])],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba um versículo aleatório do Alcorão em árabe e português.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        ayah_number = random.randint(1, self.TOTAL_AYAHS)  # noqa: S311
        lang = parsed.options.get('lang')
        url = f'https://api.alquran.cloud/v1/ayah/{ayah_number}/editions/ar.alafasy,pt.elhayek'
        response = await HttpClient.get(url)
        response.raise_for_status()
        editions = response.json()['data']
        ar_data, pt_data = editions[0], editions[1]
        surah = ar_data['surah']
        header = f'*{surah["englishName"]} {surah["number"]}:{ar_data["numberInSurah"]}*'
        return [Reply.to(data).text(self._format(header, lang, ar_data['text'], pt_data['text']))]

    @staticmethod
    def _format(header: str, lang: str | None, ar: str, pt: str) -> str:
        if lang == 'ar':
            body = f'> {ar}'
        elif lang == 'pt':
            body = f'> {pt}'
        else:
            body = f'> {ar}\n\n> {pt}'
        return f'{header}\n\n{body}'
