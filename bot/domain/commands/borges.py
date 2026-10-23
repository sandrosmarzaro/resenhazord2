from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.idempotent_counter import IdempotentCounter


class BorgesCommand(Command):
    COUNTER = IdempotentCounter('borges', 'nargas')

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='borges',
            category=Category.OTHER,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Descubra quantos nargas o Borges já fumou.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        nargas = await self.COUNTER.increment(data.message_id)
        return [Reply.to(data).text(f'Borges já fumou {nargas} nargas 🚬')]
