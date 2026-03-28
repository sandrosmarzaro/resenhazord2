import random

from bot.data.mateus import PROBABILITY_TIERS
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class MateusCommand(Command):
    MIN_PROBABILITY = 0
    MAX_PROBABILITY = 101

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='mateus', category='random', platforms=['whatsapp', 'discord'])

    @property
    def menu_description(self) -> str:
        return 'Descubra a probabilidade do Mateus nascer.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        raw = random.uniform(self.MIN_PROBABILITY, self.MAX_PROBABILITY)  # noqa: S311
        probability = f'{raw:.2f}'.replace('.', ',')
        template = next(t for threshold, t in PROBABILITY_TIERS if raw >= threshold)
        return [Reply.to(data).text(template.format(prob=probability))]
