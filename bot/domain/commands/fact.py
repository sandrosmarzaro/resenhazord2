from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class FactCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='fato', aliases=['fact'], flags=['hoje'], category='aleatórias')

    @property
    def menu_description(self) -> str:
        return 'Descubra um fato aleatório ou de hoje em inglês.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        rest_link = 'today' if 'hoje' in parsed.flags else 'random'
        url = f'https://uselessfacts.jsph.pl/api/v2/facts/{rest_link}'
        response = await HttpClient.get(url)
        response.raise_for_status()
        fact = response.json()
        return [Reply.to(data).text(f'FATO 🤓☝️\n{fact["text"]}')]
