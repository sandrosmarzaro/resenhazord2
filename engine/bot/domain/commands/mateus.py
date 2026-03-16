import random

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class MateusCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='mateus', category='aleatórias')

    @property
    def menu_description(self) -> str:
        return 'Descubra a probabilidade do Mateus nascer.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        probability = f'{random.uniform(0, 101):.2f}'.replace('.', ',')  # noqa: S311
        return [
            Reply.to(data).text(f'A probabilidade de Mateus nascer agora é de {probability} % 🧐')
        ]
