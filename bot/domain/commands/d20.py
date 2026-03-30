import random

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage


class D20Command(Command):
    DICE_SIDES = 20

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='d20', category=Category.RANDOM, platforms=[Platform.WHATSAPP, Platform.DISCORD]
        )

    @property
    def menu_description(self) -> str:
        return 'Role um dado de vinte dimensões.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        d20 = random.randint(1, self.DICE_SIDES)  # noqa: S311
        return [Reply.to(data).text(f'Aqui está sua rolada: {d20} 🎲')]
