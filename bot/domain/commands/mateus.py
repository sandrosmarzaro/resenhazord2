import random

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class MateusCommand(Command):
    MIN_PROBABILITY = 0
    MAX_PROBABILITY = 101

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='mateus', category='random')

    @property
    def menu_description(self) -> str:
        return 'Descubra a probabilidade do Mateus nascer.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        raw = random.uniform(self.MIN_PROBABILITY, self.MAX_PROBABILITY)  # noqa: S311
        probability = f'{raw:.2f}'.replace('.', ',')
        return [
            Reply.to(data).text(f'A probabilidade de Mateus nascer agora é de {probability} % 🧐')
        ]
